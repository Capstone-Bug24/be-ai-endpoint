# Operations

## Goal

Run `capruntime` as long-lived services:

- one service instance per camera
- automatic restart on failure
- per-camera environment separation

## Systemd Deployment

### 1) Prepare runtime host

```bash
sudo useradd --system --create-home --home-dir /opt/be-ai-endpoint capruntime || true
sudo mkdir -p /opt/be-ai-endpoint
sudo chown -R capruntime:capruntime /opt/be-ai-endpoint
```

### 2) Place project files

```bash
sudo rsync -a --delete ~/CapstoneProjects/be-ai-endpoint/ /opt/be-ai-endpoint/
sudo -u capruntime python3 -m venv /opt/be-ai-endpoint/.venv
sudo -u capruntime /opt/be-ai-endpoint/.venv/bin/pip install -r /opt/be-ai-endpoint/requirements.txt
```

### 3) Install service template

```bash
sudo cp /opt/be-ai-endpoint/deploy/systemd/capruntime@.service /etc/systemd/system/
sudo cp /opt/be-ai-endpoint/deploy/systemd/camera_env/cam01.env.example /etc/default/capruntime-cam01
sudo cp /opt/be-ai-endpoint/deploy/systemd/camera_env/cam02.env.example /etc/default/capruntime-cam02
```

Edit `/etc/default/capruntime-cam01` and `/etc/default/capruntime-cam02`:

- `CR_RTSP_URL`
- `CR_BACKEND_URL`
- `CR_MODEL_TYPE` and model paths if needed

### 4) Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now capruntime@cam01
sudo systemctl enable --now capruntime@cam02
```

### 5) Observe runtime

```bash
sudo systemctl status capruntime@cam01
sudo systemctl status capruntime@cam02
sudo journalctl -u capruntime@cam01 -f
sudo journalctl -u capruntime@cam02 -f
```

## Operational Commands

```bash
sudo systemctl restart capruntime@cam01
sudo systemctl restart capruntime@cam02
sudo systemctl stop capruntime@cam01
sudo systemctl stop capruntime@cam02
```

## Upgrade Procedure

```bash
sudo rsync -a --delete ~/CapstoneProjects/be-ai-endpoint/ /opt/be-ai-endpoint/
sudo -u capruntime /opt/be-ai-endpoint/.venv/bin/pip install -r /opt/be-ai-endpoint/requirements.txt
sudo systemctl restart capruntime@cam01
sudo systemctl restart capruntime@cam02
```
