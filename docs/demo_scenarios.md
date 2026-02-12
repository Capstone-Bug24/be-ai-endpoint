# Demo Scenarios

## Scenario A: Normal Event Flow

Purpose: verify that frames become events and are continuously emitted.

### Terminal 1: RTSP server

```bash
docker rm -f mediamtx >/dev/null 2>&1 || true
docker run --rm --name mediamtx -p 8554:8554 bluenviron/mediamtx:latest
```

### Terminal 2: camera stream

```bash
cd ~/CapstoneProjects/be-ai-endpoint
ffmpeg -re -stream_loop -1 -i data/samples/sample.avi -c:v h264_nvenc -preset p4 -tune ll -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/cam1
```

### Terminal 3: runtime

```bash
cd ~/CapstoneProjects/be-ai-endpoint
PYTHONPATH=src python -m capruntime --source-type rtsp --rtsp-url rtsp://127.0.0.1:8554/cam1 --camera-id cam01 --model-type mock --dry-run --output-jsonl outputs/cam01_demo.jsonl --fps-limit 10
```

### Terminal 4: verify output

```bash
cd ~/CapstoneProjects/be-ai-endpoint
tail -f outputs/cam01_demo.jsonl
```

Expected:

- runtime log is steady
- jsonl file keeps growing

## Scenario B: Backend Down, Spool Survival

Purpose: verify pipeline continues while backend is unavailable.

```bash
cd ~/CapstoneProjects/be-ai-endpoint
PYTHONPATH=src CR_BACKEND_URL=http://127.0.0.1:65500/api/events CR_DRY_RUN=false CR_SPOOL_FILE_PATH=outputs/spool/backend_down_demo.jsonl python -m capruntime --source-type file --video data/samples/sample.avi --loop --model-type mock --max-events 60
```

Verify:

```bash
cd ~/CapstoneProjects/be-ai-endpoint
wc -l outputs/spool/backend_down_demo.jsonl
```

Expected:

- runtime exits after `max-events`
- spool file exists with unsent events

## Scenario C: RTSP Reconnect

Purpose: verify runtime survives temporary input loss.

1. Start Scenario A terminals.
2. Stop Terminal 2 (camera stream) for about 10 seconds.
3. Start Terminal 2 again with the same command.
4. Check Terminal 3 runtime logs and `outputs/cam01_demo.jsonl`.

Expected:

- runtime process stays alive
- events resume after stream returns
- no manual runtime restart required

## Scenario D: Dual Camera, Dual Process

Purpose: verify architecture rule `one process = one camera`.

### camera streams

```bash
cd ~/CapstoneProjects/be-ai-endpoint
ffmpeg -re -stream_loop -1 -i data/samples/sample.avi -c:v h264_nvenc -preset p4 -tune ll -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/cam1
```

```bash
cd ~/CapstoneProjects/be-ai-endpoint
ffmpeg -re -stream_loop -1 -i data/samples/sample.avi -vf hflip -c:v h264_nvenc -preset p4 -tune ll -rtsp_transport tcp -f rtsp rtsp://127.0.0.1:8554/cam2
```

### runtimes

```bash
cd ~/CapstoneProjects/be-ai-endpoint
PYTHONPATH=src CR_SPOOL_FILE_PATH=outputs/spool/cam1_pending.jsonl python -m capruntime --source-type rtsp --rtsp-url rtsp://127.0.0.1:8554/cam1 --camera-id cam01 --model-type mock --dry-run --output-jsonl outputs/cam1_events.jsonl --fps-limit 10
```

```bash
cd ~/CapstoneProjects/be-ai-endpoint
PYTHONPATH=src CR_SPOOL_FILE_PATH=outputs/spool/cam2_pending.jsonl python -m capruntime --source-type rtsp --rtsp-url rtsp://127.0.0.1:8554/cam2 --camera-id cam02 --model-type mock --dry-run --output-jsonl outputs/cam2_events.jsonl --fps-limit 10
```

Expected:

- each process generates events independently
- one camera failure does not stop the other process
