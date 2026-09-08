"""
seed.py -- creates one demo account and one demo widget, so a stranger who just ran
`docker compose up` has something real to point curl (or customer-site/index.html) at
immediately, without first reading the API docs to figure out how to create one.
Run with:  python seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import repository
import auth


def run():
    existing = repository.get_user_by_email("demo@example.com")
    if existing:
        print("Demo account already exists (demo@example.com) -- nothing to do.")
        widgets = repository.list_widgets(tenant_id=existing["tenant_id"])
        if widgets:
            print(f"Demo widget id: {widgets[0]['id']}")
        return

    password_hash = auth.hash_password("demopassword123")
    user = repository.create_tenant_and_user("demo@example.com", password_hash, "Demo Co")
    print(f"Created demo account: demo@example.com / demopassword123 (tenant_id={user['tenant_id']})")

    widget = repository.create_widget(
        tenant_id=user["tenant_id"],
        type_="signup_form",
        title="Join our newsletter",
        description="Get one email a week, no spam.",
        fields=[{"name": "email", "label": "Email address", "required": True}],
        button_text="Sign up",
        display_options={"theme": "light"},
    )
    print(f"Created demo widget id={widget['id']} -- try it at:")
    print(f"  GET http://localhost:8000/widgets/{widget['id']}/config")
    print(f"  <script src=\"http://localhost:8000/widget.js?v=1&id={widget['id']}\"></script>")
    print("\nUpdate customer-site/index.html's script tag with this id, then serve it:")
    print("  cd customer-site && python -m http.server 5500")


if __name__ == "__main__":
    run()
