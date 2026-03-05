"""Proxy command - manage reverse proxy, Cloudflare tunnel, and BIND9 DNS."""

import click
import subprocess
import re


# Default configuration matching the shell script
DEFAULTS = {
    "proxy_server": "root@192.168.1.21",
    "bind9_server": "root@192.168.1.11",
    "nginx_conf_dir": "/etc/nginx/conf.d",
    "nginx_ssl_dir": "/etc/nginx/ssl",
    "cloudflare_config": "/etc/cloudflared/config.yml",
    "bind9_zone_file": "/etc/bind/db.nc.local",
    "tunnel_name": "nc.local-www",
    "internal_domain": "nc.local",
    "external_domain": "natcheung.com",
    "local_dns_ip": "192.168.1.21",
    "step_provisioner_password_file": "/root/.step/secrets/password",
    "step_cert_validity": "8760h",
}


def ssh_run(host, command, check=True, capture=True):
    """Run a command on a remote host via SSH."""
    ssh_cmd = [
        "ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new",
        host, command,
    ]
    result = subprocess.run(
        ssh_cmd,
        capture_output=capture,
        text=True,
        timeout=60,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        raise click.ClickException(f"SSH command failed on {host}: {stderr}")
    return result


def validate_prefix(prefix):
    """Validate domain prefix."""
    if len(prefix) < 2 or len(prefix) > 63:
        raise click.BadParameter("must be between 2-63 characters")
    if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', prefix):
        raise click.BadParameter(
            "must be lowercase alphanumeric, may contain hyphens (not at start/end)"
        )
    if '--' in prefix:
        raise click.BadParameter("cannot contain consecutive hyphens (--)")
    return prefix


def validate_endpoint(endpoint):
    """Validate service endpoint URL."""
    if not re.match(r'^https?://', endpoint):
        raise click.BadParameter("must start with http:// or https://")
    host_port = re.sub(r'^https?://', '', endpoint).split('/')[0]
    if not host_port:
        raise click.BadParameter("must have a host")
    return endpoint


def create_ssl_certificate(proxy_server, prefix, cfg):
    """Create SSL certificate using step-ca on the proxy server."""
    domain = f"{prefix}.{cfg['internal_domain']}"
    cert_file = f"{cfg['nginx_ssl_dir']}/{domain}.crt"
    key_file = f"{cfg['nginx_ssl_dir']}/{domain}.key"

    click.echo(f"  Creating SSL certificate for {domain}...")

    # Ensure SSL directory exists
    ssh_run(proxy_server, f"mkdir -p {cfg['nginx_ssl_dir']}")

    # Check prerequisites
    ssh_run(proxy_server, "command -v step")
    ssh_run(proxy_server, "step ca health")
    ssh_run(proxy_server, f"test -f {cfg['step_provisioner_password_file']}")

    # Check if valid certificate already exists
    check_cmd = f"""
if [ -f "{cert_file}" ]; then
    if step certificate inspect "{cert_file}" --format json 2>/dev/null | \
       python3 -c "import sys,json,datetime; d=json.load(sys.stdin); exp=datetime.datetime.fromisoformat(d['validity']['end'].replace('Z','+00:00')); sys.exit(0 if exp > datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30) else 1)" 2>/dev/null; then
        echo "VALID"
    else
        echo "EXPIRED"
    fi
else
    echo "MISSING"
fi
"""
    result = ssh_run(proxy_server, check_cmd)
    status = result.stdout.strip()

    if status == "VALID":
        click.echo(f"  Valid certificate already exists for {domain}, skipping")
        return

    if status == "EXPIRED":
        click.echo(f"  Certificate expired or expiring soon, renewing...")

    # Create certificate
    create_cmd = (
        f'step ca certificate "{domain}" "{cert_file}" "{key_file}" '
        f'--provisioner-password-file="{cfg["step_provisioner_password_file"]}" '
        f'--not-after="{cfg["step_cert_validity"]}" --force'
    )
    ssh_run(proxy_server, create_cmd)
    ssh_run(proxy_server, f'chmod 644 "{cert_file}" && chmod 600 "{key_file}"')

    click.echo(f"  SSL certificate created: {cert_file}")


def configure_nginx(proxy_server, prefix, endpoint, cfg):
    """Configure Nginx reverse proxy with HTTPS."""
    domain = f"{prefix}.{cfg['internal_domain']}"
    conf_file = f"{cfg['nginx_conf_dir']}/{domain}.conf"
    cert_file = f"{cfg['nginx_ssl_dir']}/{domain}.crt"
    key_file = f"{cfg['nginx_ssl_dir']}/{domain}.key"

    click.echo(f"  Configuring Nginx for {domain}...")

    # Backup existing config
    ssh_run(proxy_server, f'test -f "{conf_file}" && cp "{conf_file}" "{conf_file}.bak" || true')

    nginx_conf = f"""# HTTP -> HTTPS redirect
server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}

# HTTPS server
server {{
    listen 443 ssl http2;
    server_name {domain};

    # SSL Configuration
    ssl_certificate {cert_file};
    ssl_certificate_key {key_file};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HSTS - enforce HTTPS in browsers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Health check endpoint
    location = /health {{
        return 200 "ok";
        add_header Content-Type text/plain;
    }}

    # Proxy to backend service
    location / {{
        proxy_pass {endpoint};

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""

    # Write config via SSH using heredoc
    write_cmd = f"cat > '{conf_file}' << 'NGINXEOF'\n{nginx_conf}NGINXEOF"
    ssh_run(proxy_server, write_cmd)

    # Test nginx config
    result = ssh_run(proxy_server, "nginx -t 2>&1", check=False)
    if result.returncode != 0:
        # Restore backup
        ssh_run(proxy_server, f'test -f "{conf_file}.bak" && mv "{conf_file}.bak" "{conf_file}" || true')
        raise click.ClickException(f"Nginx config test failed: {result.stdout} {result.stderr}")

    click.echo(f"  Nginx configured: {conf_file}")


def configure_cloudflare(proxy_server, prefix, endpoint, cfg):
    """Configure Cloudflare tunnel."""
    domain = f"{prefix}.{cfg['external_domain']}"
    cf_config = cfg['cloudflare_config']

    click.echo(f"  Configuring Cloudflare for {domain}...")

    # Check if already exists
    result = ssh_run(proxy_server, f'grep -q "hostname: {domain}" "{cf_config}"', check=False)
    if result.returncode == 0:
        click.echo(f"  Hostname {domain} already exists in Cloudflare config")
    else:
        # Backup and add entry
        ssh_run(proxy_server, f'cp "{cf_config}" "{cf_config}.bak"')
        add_cmd = f"""awk -v hostname="{domain}" -v service="{endpoint}" '
            /service: http_status:404/ {{
                print "  - hostname: " hostname
                print "    service: " service
            }}
            {{ print }}
        ' "{cf_config}" > "{cf_config}.tmp" && mv "{cf_config}.tmp" "{cf_config}" """
        ssh_run(proxy_server, add_cmd)
        click.echo(f"  Added {domain} to Cloudflare config")

    # Create DNS route
    result = ssh_run(
        proxy_server,
        f'cloudflared tunnel route dns "{cfg["tunnel_name"]}" "{domain}" 2>&1',
        check=False,
    )
    if result.returncode == 0:
        click.echo(f"  DNS route created for {domain}")
    else:
        click.echo(f"  DNS route may already exist for {domain}")


def configure_bind9(proxy_server, prefix, cfg):
    """Configure BIND9 DNS record."""
    domain = f"{prefix}.{cfg['internal_domain']}"
    bind9_server = cfg['bind9_server']
    zone_file = cfg['bind9_zone_file']
    dns_ip = cfg['local_dns_ip']

    click.echo(f"  Configuring BIND9 for {domain} -> {dns_ip}...")

    # Check BIND9 server reachable (from proxy server)
    ssh_run(proxy_server, f'ssh -o ConnectTimeout=5 {bind9_server} "echo ok"')

    # Check zone file exists
    ssh_run(proxy_server, f'ssh {bind9_server} "test -f {zone_file}"')

    # Check if entry already exists
    result = ssh_run(
        proxy_server,
        f"""ssh {bind9_server} "grep -q '^{prefix}[[:space:]]' {zone_file}" """,
        check=False,
    )
    if result.returncode == 0:
        click.echo(f"  Entry {prefix} already exists in BIND9 zone file")
        return

    # Add A record
    ssh_run(
        proxy_server,
        f"""ssh {bind9_server} "printf '%s\\t\\tIN\\tA\\t%s\\n' '{prefix}' '{dns_ip}' >> {zone_file}" """,
    )

    # Update serial
    serial_cmd = f"""ssh {bind9_server} '
        CURRENT_SERIAL=$(grep -oP "^\\s+\\K[0-9]+(?=\\s*;\\s*Serial)" {zone_file})
        if [ -z "$CURRENT_SERIAL" ]; then
            TODAY=$(date +%Y%m%d)
            CURRENT_SERIAL="${{TODAY}}00"
        fi
        NEW_SERIAL=$((CURRENT_SERIAL + 1))
        sed -i "s/${{CURRENT_SERIAL}}.*Serial/${{NEW_SERIAL}}\\t\\t; Serial/" {zone_file}
        echo "Serial updated: ${{CURRENT_SERIAL}} -> ${{NEW_SERIAL}}"
    '"""
    result = ssh_run(proxy_server, serial_cmd)
    if result.stdout.strip():
        click.echo(f"  {result.stdout.strip()}")

    # Verify zone file
    result = ssh_run(
        proxy_server,
        f'ssh {bind9_server} "named-checkzone {cfg["internal_domain"]} {zone_file}"',
        check=False,
    )
    if result.returncode == 0:
        click.echo(f"  Zone file syntax OK")
    else:
        click.echo(f"  Warning: Zone file syntax check returned issues", err=True)

    click.echo(f"  Added {prefix} A record -> {dns_ip}")


def restart_services(proxy_server, prefix, mode, cfg):
    """Restart affected services."""
    bind9_server = cfg['bind9_server']
    domain = f"{prefix}.{cfg['internal_domain']}"
    dns_ip = cfg['local_dns_ip']

    click.echo("  Restarting services...")

    # Restart BIND9
    ssh_run(proxy_server, f'ssh {bind9_server} "systemctl restart named"')
    click.echo("  BIND9 restarted")

    # Verify DNS
    result = ssh_run(
        proxy_server,
        f'ssh {bind9_server} "dig @localhost {domain} +short"',
        check=False,
    )
    resolved_ip = result.stdout.strip() if result.stdout else ""
    if resolved_ip == dns_ip:
        click.echo(f"  DNS verified: {domain} -> {resolved_ip}")
    else:
        click.echo(f"  DNS resolution: {resolved_ip or 'empty'} (expected {dns_ip})")

    # Reload Nginx
    if mode in ("nginx", "both"):
        ssh_run(proxy_server, "systemctl reload nginx")
        click.echo("  Nginx reloaded")

    # Restart Cloudflared
    if mode in ("cloudflare", "both"):
        ssh_run(proxy_server, "systemctl restart cloudflared")
        click.echo("  Cloudflared restarted")


def verify_https(proxy_server, prefix, cfg):
    """Verify HTTPS is working."""
    domain = f"{prefix}.{cfg['internal_domain']}"
    dns_ip = cfg['local_dns_ip']

    click.echo(f"  Verifying HTTPS for {domain}...")

    result = ssh_run(
        proxy_server,
        f'curl -sk "https://{domain}/health" --resolve "{domain}:443:{dns_ip}" 2>/dev/null',
        check=False,
    )
    if result.stdout and "ok" in result.stdout:
        click.echo(f"  HTTPS working: https://{domain}")
    else:
        click.echo(f"  Could not verify HTTPS (service may not be running yet)")


@click.command()
@click.argument('prefix')
@click.argument('endpoint')
@click.argument('mode', type=click.Choice(['nginx', 'cloudflare', 'both'], case_sensitive=False))
@click.option(
    '--proxy-server',
    default=DEFAULTS['proxy_server'],
    help=f"Nginx/Cloudflare server (default: {DEFAULTS['proxy_server']})",
)
@click.option(
    '--bind9-server',
    default=DEFAULTS['bind9_server'],
    help=f"BIND9 DNS server (default: {DEFAULTS['bind9_server']})",
)
@click.option(
    '--dns-ip',
    default=DEFAULTS['local_dns_ip'],
    help=f"IP for DNS A records (default: {DEFAULTS['local_dns_ip']})",
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be done without making changes',
)
def proxy(prefix, endpoint, mode, proxy_server, bind9_server, dns_ip, dry_run):
    """
    Set up reverse proxy, DNS, and optional Cloudflare tunnel.

    Creates Nginx HTTPS reverse proxy with step-ca SSL certificates,
    BIND9 DNS A records, and optionally Cloudflare tunnel entries.

    \b
    Arguments:
      PREFIX    Domain prefix (e.g. 'myapp' for myapp.nc.local)
      ENDPOINT  Backend service URL (e.g. http://192.168.1.61:3000)
      MODE      One of: nginx, cloudflare, both

    \b
    Modes:
      nginx      - Nginx + SSL + BIND9 DNS (internal only)
      cloudflare - Nginx + SSL + Cloudflare tunnel + BIND9
      both       - Same as cloudflare

    \b
    Examples:
        nccli proxy myapp http://192.168.1.61:3000 nginx
        nccli proxy myapp http://192.168.1.61:3000 both
        nccli proxy myapp http://192.168.1.61:3000 nginx --dry-run
    """
    # Validate inputs
    try:
        validate_prefix(prefix)
    except click.BadParameter as e:
        raise click.ClickException(f"Invalid prefix '{prefix}': {e.format_message()}")

    try:
        validate_endpoint(endpoint)
    except click.BadParameter as e:
        raise click.ClickException(f"Invalid endpoint '{endpoint}': {e.format_message()}")

    mode = mode.lower()
    if mode == "both":
        mode = "cloudflare"  # 'both' is an alias for 'cloudflare'

    cfg = dict(DEFAULTS)
    cfg['bind9_server'] = bind9_server
    cfg['local_dns_ip'] = dns_ip

    internal_url = f"https://{prefix}.{cfg['internal_domain']}"
    external_url = f"https://{prefix}.{cfg['external_domain']}"

    click.echo("=" * 50)
    click.echo("Domain Management")
    click.echo("=" * 50)
    click.echo(f"Prefix:   {prefix}")
    click.echo(f"Service:  {endpoint}")
    click.echo(f"Mode:     {mode}")
    click.echo(f"Server:   {proxy_server}")
    click.echo(f"DNS IP:   {dns_ip}")
    click.echo("=" * 50)

    if dry_run:
        click.echo("")
        click.echo("Dry run - would perform:")
        click.echo(f"  1. Create SSL cert for {prefix}.{cfg['internal_domain']}")
        click.echo(f"  2. Create Nginx HTTPS config -> {endpoint}")
        if mode == "cloudflare":
            click.echo(f"  3. Add Cloudflare tunnel entry for {prefix}.{cfg['external_domain']}")
        click.echo(f"  {'4' if mode == 'cloudflare' else '3'}. Add BIND9 A record: {prefix} -> {dns_ip}")
        click.echo(f"  {'5' if mode == 'cloudflare' else '4'}. Restart services")
        click.echo("")
        click.echo(f"Internal URL: {internal_url}")
        if mode == "cloudflare":
            click.echo(f"External URL: {external_url}")
        return

    try:
        # Check proxy server connectivity
        click.echo("")
        click.echo(f"Connecting to {proxy_server}...")
        ssh_run(proxy_server, "echo ok")

        # Step 1: SSL Certificate
        click.echo("")
        click.echo("[1/5] SSL Certificate")
        create_ssl_certificate(proxy_server, prefix, cfg)

        # Step 2: Nginx
        click.echo("")
        click.echo("[2/5] Nginx Configuration")
        configure_nginx(proxy_server, prefix, endpoint, cfg)

        # Step 3: Cloudflare (if applicable)
        click.echo("")
        if mode == "cloudflare":
            click.echo("[3/5] Cloudflare Tunnel")
            configure_cloudflare(proxy_server, prefix, endpoint, cfg)
        else:
            click.echo("[3/5] Cloudflare Tunnel (skipped - nginx mode)")

        # Step 4: BIND9
        click.echo("")
        click.echo("[4/5] BIND9 DNS")
        configure_bind9(proxy_server, prefix, cfg)

        # Step 5: Restart & Verify
        click.echo("")
        click.echo("[5/5] Restart Services & Verify")
        restart_services(proxy_server, prefix, "both" if mode == "cloudflare" else "nginx", cfg)
        verify_https(proxy_server, prefix, cfg)

        # Summary
        click.echo("")
        click.echo("=" * 50)
        click.echo("Configuration completed!")
        click.echo("=" * 50)
        click.echo(f"Internal URL: {internal_url}")
        if mode == "cloudflare":
            click.echo(f"External URL: {external_url}")
        cert_path = f"{cfg['nginx_ssl_dir']}/{prefix}.{cfg['internal_domain']}.crt"
        click.echo(f"SSL Cert:     {cert_path}")
        click.echo(f"Validity:     {cfg['step_cert_validity']}")

    except click.ClickException:
        raise
    except subprocess.TimeoutExpired:
        raise click.ClickException("SSH command timed out")
    except Exception as e:
        raise click.ClickException(str(e))
