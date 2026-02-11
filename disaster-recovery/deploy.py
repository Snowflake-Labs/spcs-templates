#!/usr/bin/env python3
"""
SPCS Disaster Recovery Deployment

Prerequisites:
    Define connections in ~/.snowflake/config.toml:
        [connections.snowflake_primary]
        account = "your-org-your-primary-account"
        user = "..."
        role = "ACCOUNTADMIN"   # Required for failover group setup
        
        [connections.snowflake_secondary]
        account = "your-org-your-secondary-account"
        user = "..."
        role = "ACCOUNTADMIN"   # Required for failover group setup

Usage:
    # One-time setup (run in order)
    python deploy.py setup primary
    python deploy.py setup secondary

    # Service deployment (repeatable)
    python deploy.py service primary
    python deploy.py service secondary
    python deploy.py service all

    # Failover (disaster recovery)
    python deploy.py failover   # Promotes secondary to primary

Script naming convention:
    *_primary_*   - only runs for primary
    *_secondary_* - only runs for secondary
    (no marker)   - runs for both
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


def load_config(base_path: Path, role: str) -> dict:
    """Load and merge base config with role-specific overrides."""
    with open(base_path / "config/base.yml") as f:
        config = yaml.safe_load(f)
    with open(base_path / f"config/targets/{role}.yml") as f:
        role_config = yaml.safe_load(f)
    
    for key, value in role_config.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value
    
    # Load both configs to get primary/secondary accounts
    for r in ["primary", "secondary"]:
        with open(base_path / f"config/targets/{r}.yml") as f:
            config[f"{r}_account"] = yaml.safe_load(f)["account"]
    
    return config


def execute_sql(sql: str, connection: str, dry_run: bool) -> bool:
    """Execute SQL via Snow CLI."""
    if dry_run:
        print(f"[DRY RUN]\n{sql}\n")
        return True
    
    try:
        result = subprocess.run(
            ["snow", "sql", "-c", connection, "-q", sql],
            capture_output=True, text=True, check=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {e.stderr}")
        return False


def run_flow(flow: str, role: str, base_path: Path, dry_run: bool) -> bool:
    """Run a deployment flow for a role."""
    config = load_config(base_path, role)
    connection = config["connection"]["name"]
    
    env = Environment(loader=FileSystemLoader(base_path / "scripts"))
    flow_path = base_path / "scripts" / flow
    
    print(f"\n[{flow}/{role}]")
    
    for script in sorted(flow_path.glob("*.sql")):
        name = script.name
        if "_primary_" in name and role != "primary":
            continue
        if "_secondary_" in name and role != "secondary":
            continue
        
        print(f"  >> {name}")
        sql = env.get_template(f"{flow}/{name}").render(**config)
        if not execute_sql(sql, connection, dry_run):
            return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="SPCS Disaster Recovery Deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy.py setup primary      # Run first
  python deploy.py setup secondary    # Run second
  python deploy.py service all        # Deploy to both
  python deploy.py failover           # Promote secondary to primary
        """
    )
    parser.add_argument("flow", choices=["setup", "service", "failover"], 
                        help="setup: one-time setup, service: deploy/update service, failover: promote secondary")
    parser.add_argument("target", choices=["primary", "secondary", "all"], nargs="?",
                        help="Target account (required for setup/service, not used for failover)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Print SQL without executing")
    args = parser.parse_args()
    
    base_path = Path(__file__).parent
    
    # Failover runs against both: suspend primary (best effort), then promote secondary
    if args.flow == "failover":
        # Try to suspend primary - ignore failures (primary may be inaccessible)
        print("\n[failover/primary] (best effort - may fail if primary is down)")
        run_flow("failover", "primary", base_path, args.dry_run)
        
        # Promote secondary - this must succeed
        if not run_flow("failover", "secondary", base_path, args.dry_run):
            sys.exit(1)
        print("\nDone")
        return
    
    # Other flows require a target
    if not args.target:
        print("ERROR: Target required for setup/service flows")
        print("  python deploy.py setup primary")
        print("  python deploy.py service all")
        sys.exit(1)
    
    if args.target == "all":
        if args.flow == "setup":
            print("ERROR: Setup must be run per-target in order:")
            print("  1. python deploy.py setup primary")
            print("  2. python deploy.py setup secondary")
            sys.exit(1)
        targets = ["primary", "secondary"]
    else:
        targets = [args.target]
    
    for target in targets:
        if not run_flow(args.flow, target, base_path, args.dry_run):
            sys.exit(1)
    
    print("\nDone")


if __name__ == "__main__":
    main()
