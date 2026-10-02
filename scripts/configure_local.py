"""Create a local secret once; never rewrite existing configuration."""

from pathlib import Path
import argparse
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true", help="Create ignored .env.docker with an independent secret")
    args = parser.parse_args()
    path = ROOT / (".env.docker" if args.docker else "backend/.env")
    if path.exists():
        print(f"Existing {path.name} preserved, including mode and signing key.")
        return
    example = "JWT_SECRET_KEY=\nSCOUTAI_DEMO_MODE=true\n" if args.docker else (ROOT / "backend/.env.example").read_text(encoding="utf-8")
    content = example.replace("JWT_SECRET_KEY=\n", f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}\n")
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)
    print("Created private local configuration: DEMO mode, no seeded accounts, no model download.")


if __name__ == "__main__":
    main()
