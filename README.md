Star Resonance Relay
====================

A one-way chat relay between in-game chat → Discord chat for Blue Protocol: Star Resonance.

## Installing dependencies

### Windows

Install [npcap](https://npcap.com/)

### Linux

Install `libpcap` library

#### Debian / Ubuntu

```bash
apt-get install libpcap
```

#### Arch

```bash
pacman -S libpcap
```

## Usage

### Initial setup

1. Generate BPSR protocol buffers
   ```bash
   uv run scripts/generate_protobufs.py
   ```

2. Copy `.env.example` and rename it to `.env`
3. In `.env`, replace the `WEBHOOK_URL` value with the webhook on Discord side.

### Running

#### With uv

```bash
uv run --env .env star-resonance-relay
```

#### With Docker Compose (only on Linux)

```bash
docker compose up -d
```
