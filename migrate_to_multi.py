import asyncio
import json
from typing import Any

from app.db import Database
from app.xui import XuiClient, XuiError

async def migrate_order(db: Database, order: dict, old_loc: Any, new_loc: Any) -> bool:
    order_id = order["id"]
    email = order["xui_email"]
    status = order["status"]
    
    # If the order hasn't been provisioned yet, we just update the DB
    if status != "provisioned" or not email:
        db._conn.execute("UPDATE orders SET location_id = ? WHERE id = ?", (new_loc.id, order_id))
        db._conn.commit()
        return True

    # Check if they use the same panel (base_url and token)
    same_panel = (old_loc.base_url == new_loc.base_url and old_loc.api_token == new_loc.api_token)
    
    try:
        if same_panel:
            # If same panel, we just update the inboundIds for this client
            async with XuiClient(new_loc.base_url, new_loc.api_token) as xui:
                await xui.update_client(email=email, inbound_ids=new_loc.inbound_ids)
                
                # The subLinks will naturally contain all the new inbounds now.
                # We need to fetch the updated sub_links to save in DB.
                sub_id = order["xui_sub_id"]
                new_links = []
                if sub_id:
                    new_links = await xui.get_sub_links(sub_id)
                
                db._conn.execute(
                    "UPDATE orders SET location_id = ?, sub_links = ? WHERE id = ?", 
                    (new_loc.id, json.dumps(new_links), order_id)
                )
                db._conn.commit()
                return True
        else:
            # Different panel: fetch usage from old, delete from old, create on new
            async with XuiClient(old_loc.base_url, old_loc.api_token) as old_xui:
                usage = await old_xui.get_usage(email)
                await old_xui.delete_client(email)
                
            async with XuiClient(new_loc.base_url, new_loc.api_token) as new_xui:
                await new_xui.add_client(
                    email=email,
                    volume_gb=int(order["volume_gb"]),
                    duration_days=int(order["duration_days"]),
                    inbound_ids=new_loc.inbound_ids,
                    tg_user_id=int(order["user_id"]),
                    expiry_time_ms=usage.expiry_time_ms,
                    total_bytes=usage.total_bytes,
                    client_uuid=order["xui_client_uuid"],
                    sub_id=order["xui_sub_id"]
                )
                
                sub_id = order["xui_sub_id"]
                new_links = []
                if sub_id:
                    new_links = await new_xui.get_sub_links(sub_id)
                
                db._conn.execute(
                    "UPDATE orders SET location_id = ?, sub_links = ? WHERE id = ?", 
                    (new_loc.id, json.dumps(new_links), order_id)
                )
                db._conn.commit()
                return True

    except Exception as e:
        print(f"❌ Failed to migrate order #{order_id}: {e}")
        return False


async def main():
    print("🔍 Opening database...")
    db = Database("netfly.db")
    locations = db.list_locations(only_enabled=False)
    
    print("\n🌍 Available Locations:")
    for loc in locations:
        print(f"ID: {loc.id} | Name: {loc.name}")
        
    try:
        old_loc_id = int(input("\n➡️ Enter the OLD location ID to migrate FROM: "))
        new_loc_id = int(input("➡️ Enter the NEW multi-location ID to migrate TO: "))
    except ValueError:
        print("Invalid input.")
        return
        
    old_loc = db.get_location(old_loc_id)
    new_loc = db.get_location(new_loc_id)
    
    if not old_loc or not new_loc:
        print("Invalid location IDs specified.")
        return
        
    # Get all orders for the old location
    db._conn.row_factory = dict_factory
    orders = db._conn.execute("SELECT * FROM orders WHERE location_id = ?", (old_loc_id,)).fetchall()
    
    if not orders:
        print(f"No orders found for Location ID {old_loc_id}.")
        return
        
    print(f"\n📦 Found {len(orders)} orders to migrate from '{old_loc.name}' to '{new_loc.name}'.")
    confirm = input("Continue? (y/n): ")
    if confirm.lower() != 'y':
        return
        
    migrated = 0
    for order in orders:
        print(f"Migrating Order #{order['id']}...")
        success = await migrate_order(db, order, old_loc, new_loc)
        if success:
            migrated += 1
            
    print(f"\n✅ Migration complete! Successfully migrated {migrated}/{len(orders)} orders.")


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


if __name__ == "__main__":
    asyncio.run(main())
