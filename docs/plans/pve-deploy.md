# Vowen dedicated PVE Spain deployment

User explicitly authorized a new LXC, nginx-ui domain and BotFather Mini App settings; switched infrastructure operations to SSH. Preserve existing infrastructure and application access invariants. Infra AGENTS and operating brief apply; never read infra/.env or unrelated credentials.

1. Live audit -> fresh unprivileged Debian13 guest,2CPU4GiB32GiB, owner-selected unused ID/address. Guest-only persistent nft boundary permits HTTP solely from the nginx edge, blocks private egress except LAN DNS; no PVE/OPNsense global firewall changes. Validate ingress/egress and reboot.
2. Deploy frozen Vowen source/Compose behind private Caddy HTTP with trusted edge source only. Fresh independent DB/keyring and existing Vowen bot token via protected transport, no seeded users or developer auth bypass. Validate migrations, API/static, body caps, unauthenticated denials and secret-file denial.
3. Back up nginx edge configuration, new vowen.sh-inc.ru vhost and nginx-ui-managed cert; verify public and LAN TLS without bypass. Configure already-selected @Vowen_Bot Mini App through user-opened BotFather. No token rotation or unrelated bot changes.
4. Review deployment diff, gates/greenCI/commits; update Vowen status and environment wiki. Separate live participant tests: participant Telegram IDs/names and personal consent required; operator never creates consent. Backup+restore acceptance must be explicit evidence.
