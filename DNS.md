# DNS — littleblueletter.com → GitHub Pages

Verified **2026-09-29** via OVH `v1_domain` MCP (`Documents/server/scripts/ovh-domain-mcp.py`).

**Apex A (TTL 300):** GitHub Pages `185.199.108.153` … `.111.153`  
**Apex AAAA:** `2606:50c0:8000::153` … `8003::153`  
**www CNAME:** `glen-w.github.io.`

Kept: NS `dns111`/`ns111`, MX (OVH mail), SPF.

Removed: OVH parking / HTTP-only redirection A `213.186.33.5` and redirect TXT (`4|https://…`).

HTTPS: GitHub Pages custom-domain cert for apex + www; enforce HTTPS on.
