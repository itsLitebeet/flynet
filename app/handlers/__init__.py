from aiogram import Router

from app.handlers import admin, admin_panel, my_services, order, review, start, support


def build_root_router() -> Router:
    """Combine all feature routers into a single router for the dispatcher.

    Order matters slightly: state-scoped handlers in `order`, `review` and
    `my_services` are evaluated before the generic command/menu handlers,
    so things like /cancel inside an FSM flow are caught first.
    """
    root = Router(name="root")
    root.include_router(order.router)
    root.include_router(review.router)
    root.include_router(my_services.router)
    root.include_router(start.router)
    root.include_router(support.router)
    root.include_router(admin_panel.router)
    root.include_router(admin.router)
    return root
