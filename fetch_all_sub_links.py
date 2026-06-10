import asyncio
import json
import sqlite3
from app.db import Database
from app.xui import XuiClient

async def main():
    print("🔍 Opening database...")
    db = Database("netfly.db")
    
    # Fetch all active/provisioned orders
    db._conn.row_factory = sqlite3.Row
    orders = db._conn.execute(
        "SELECT id, location_id, xui_email, xui_sub_id, status FROM orders WHERE status = 'provisioned' AND is_test = 0"
    ).fetchall()
    
    if not orders:
        print("No active provisioned orders found.")
        return
        
    print(f"📦 Found {len(orders)} active orders to update.")
    
    # Group locations to reuse XuiClient connections
    locations_cache = {}
    
    updated_count = 0
    failed_count = 0
    
    for order in orders:
        order_id = order["id"]
        loc_id = order["location_id"]
        email = order["xui_email"]
        sub_id = order["xui_sub_id"]
        
        if not email or not sub_id:
            print(f"⚠️ Order #{order_id} is missing panel email or sub_id. Skipping.")
            continue
            
        # Get location
        if loc_id not in locations_cache:
            loc = db.get_location(loc_id)
            if not loc:
                print(f"❌ Location ID {loc_id} not found in database for Order #{order_id}.")
                continue
            locations_cache[loc_id] = loc
            
        loc = locations_cache[loc_id]
        
        print(f"🔄 Fetching sub-links for Order #{order_id} ({email}) from server '{loc.name}'...")
        
        try:
            async with XuiClient(loc.base_url, loc.api_token) as xui:
                new_links = await xui.get_sub_links(sub_id)
                if new_links:
                    db._conn.execute(
                        "UPDATE orders SET sub_links = ?, updated_at = datetime('now') WHERE id = ?",
                        (json.dumps(new_links), order_id)
                    )
                    db._conn.commit()
                    print(f"  [SUCCESS] Updated {len(new_links)} sub-links for Order #{order_id}.")
                    updated_count += 1
                else:
                    print(f"  [WARNING] Received empty links list for Order #{order_id} (subId: {sub_id}).")
                    failed_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to fetch links for Order #{order_id}: {e}")
            failed_count += 1
            
    print(f"\n✅ Done! Successfully updated {updated_count} orders. Failed/Skipped: {failed_count}.")

if __name__ == "__main__":
    asyncio.run(main())
