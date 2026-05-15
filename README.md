Star Resonance Chat Relay
=========================

A one-way chat relay between in-game chat → Discord chat for Blue Protocol: Star Resonance.

![Demo](./.github/.meta/demo.png)

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [npcap](https://npcap.com/) (Windows) / libpcap (Linux)

## Running

### Initial setup

1. Update git submodules.
   ```bash
   git submodule update --init --recursive
   ```
2. Generate BPSR protocol buffers.
   ```bash
   uv run --group build scripts/generate_protobufs.py
   ```
3. Copy `.env.example` and rename it to `.env`.
4. In `.env`,
   - Replace `WEBHOOK_URL` value with the webhook on Discord side.
   - Replace `CHANNEL_TYPE` value with the channel types separated by `,` to relay the message.
     Supported: `World`, `Guild`, `Team`, `Current`

### Running

```bash
uv run --env-file .env star-resonance-relay
```

## In-game Setup

- Chat message sniffing works in any menu.
- Avatar images require opening the chat and loading the image.

### Recommended Setup

1. Toggle all channels for General tab.
   ![Chat settings](./.github/.meta/chat-settings.png)
2. Keep the General chat tab open.
   ![Chat setup](./.github/.meta/chat-setup.png)

## Extending

The main logic is separated into packet handling and packet sniffing logics.

Example usage can be seen in `bot.py` for handling the callback from `BPSRSniffer`

## Limitations

⚠️ As the code is written in Python and uses scapy for packet sniffing (with known performance limitation
https://scapy.readthedocs.io/en/latest/usage.html#performance-of-scapy), packets are prone to be lost 
and skipped during the sniffing process. The performance of the tool heavily depends on how
capable the host machine is.

There is ongoing plan to rewrite it in a more performant language, but it depends on how lazy
I am. :P

## Disclaimer

This project is in no form related, associated, or endorsed by the developer and publisher of Blue Protocol: Star Resonance.
The project is created for educational purposes only and heavily uses packet sniffing.

