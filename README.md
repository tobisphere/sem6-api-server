on raspberry pi turn on funnel for external access:
sudo tailscale funnel 80
it produces this link: 
https://raspberrypi.tail1480d1.ts.net/

# Image Upload API

This project runs an image upload server that automatically checks whether uploaded images are safe using an AI model. It uses **FastAPI** (the backend), **Nginx** (a reverse proxy that handles incoming requests), and **Docker** (which packages everything so it runs the same way on any machine).

## Dependencies
- [Git](https://git-scm.com/install/)
- [Docker](https://docs.docker.com/engine/install/)
- [Docker compose](https://docs.docker.com/compose/install/)

## Step 2 — Clone Repo

If you have `git` installed, clone the repository:

```bash
git clone <https://github.com/tobisphere/sem6-api-server.git>
cd <sem6-api-server>
```

## Step 3 — Create the Uploads Folder

The project saves uploaded images to a folder on your machine. You need to create it first:

```bash
sudo mkdir -p /mnt/storage/sem6-api-server/uploads
sudo chmod 777 /mnt/storage/sem6-api-server/uploads
```

> If you want to use a different folder, open `docker-compose.yml` and change the left side of the volume line under `fastapi`:
> ```yaml
> volumes:
>     - /your/custom/path:/api/uploads
> ```

## Step 4 — Add the AI Model

The project needs a trained model file to check whether images are safe. Place the file at:

```
app/model/resnet18_sketch_model.pth
```

Your folder structure should look like this:

```
.
├── app/
│   ├── model/
│   │   └── resnet18_sketch_model.pth   ← file goes here
│   ├── main.py
│   └── ...
└── docker-compose.yml
```

## Step 5 — Build and Start the Project

Make the build script executable and run it:

```bash
chmod +x build.sh
sudo ./build.sh
```

This will:
1. Build the Docker images from scratch
2. Start both the FastAPI server and Nginx
3. Show you the logs so you can confirm everything started correctly

You should see lines like:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

That means the server is running.

---

## Step 6 — Using the API

Once the server is running, you can access it from your browser or any tool like `curl`.

Replace `localhost` with your machine's IP address or hostname if accessing from another device.

### Check the server is alive

```
GET http://localhost/health
```

Expected response:
```json
"healthy"
```

### Upload an image

```bash
curl -X POST http://localhost/app/upload \
  -F "file=@/path/to/your/image.png"
```

The server will analyse the image and either accept or reject it. If accepted, it is saved to the uploads folder.

Example accepted response:
```json
{
  "status": "accepted",
  "prediction": "safe",
  "confidence": 0.97,
  "message": "File uploaded and validated successfully."
}
```

Example rejected response:
```json
{
  "status": "rejected",
  "prediction": "unsafe",
  "confidence": 0.91,
  "message": "File rejected: detected as unsafe content"
}
```

### Fetch the most recent image

```
GET http://localhost/app/fetch
```

This returns the latest uploaded image file.

### Fetch a specific image by position

```
GET http://localhost/app/fetchi/1
```

- `/1` = most recently uploaded image
- `/2` = second most recent
- `/3` = third most recent

The server keeps a maximum of **3 images** at a time. Older ones are automatically deleted when a new one is saved. You can change this inside the main.py file at MAX_IMAGES.

### List all stored images

```
GET http://localhost/app/fetch_all
```

Returns a JSON list of all stored images with their filenames, sizes, and timestamps.

### Browse the interactive API docs

Open this in your browser:

```
http://localhost/docs
```

This gives you a visual interface to try every endpoint without needing to use `curl`.

## Stopping the Server

```bash
sudo docker compose down
```

## Restarting After Changes

If you edit any file (like `main.py` or `nginx.conf`), rebuild and restart with:

```bash
sudo ./build.sh
```

## Viewing Logs

To see what the API server is doing:

```bash
sudo docker logs api-monitizer
```

To see what Nginx is doing:

```bash
sudo docker logs nginx
```

To follow the logs in real time (press `Ctrl+C` to stop):

```bash
sudo docker logs -f api-monitizer
```

## Troubleshooting

| Problem | What to check |
|---|---|
| `docker: command not found` | Re-run Step 1 |
| `permission denied` on build.sh | Run `chmod +x build.sh` first |
| 404 on `/app/fetchi/1` | Make sure the uploads folder exists and has images in it |
| Model error on startup | Check that `app/model/resnet18_sketch_model.pth` exists |
| Port 80 already in use | Stop any other web server: `sudo systemctl stop apache2` or `sudo systemctl stop nginx` |
| Images not saving | Check the uploads folder path in `docker-compose.yml` matches the folder you created |
| 'CORS Failed' on api call | Add current origin to the origins list at main.py | 

## Disclaimer

This setup is not safe! Please only use on local network, or with trusted devices.

## Making the Server Accessible (optional)
 
By default the server only works on your local network. If you want to reach it from another location, you have a few options. They vary a lot in how safe they are.
 
### Tailscale
 
This is the approach used in this project and the safest option for most people.
 
Tailscale creates a private encrypted network (called a Tailnet) between your devices. Your server never gets a public IP address — it is only reachable by devices you have personally added to your Tailnet. This means you get remote access without opening any ports or exposing anything to the internet.
 
**Install Tailscale on the server:**
 
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
 
Follow the link it prints to log in and authorise the machine. Once connected, Tailscale gives your server a private hostname like `raspberrypi.tail1234.ts.net`.
 
**Install Tailscale on the device you want to access from** (phone, laptop, etc.) using the app from [tailscale.com/download](https://tailscale.com/download) and log in with the same account.
 
You can then reach your server at:
 
```
http://raspberrypi.tail1234.ts.net/app/fetch
```
 
**Why this is safer than the alternatives:**
- No ports are forwarded on your router
- No public IP is exposed
- Only logged-in Tailscale devices on your account can connect
- Traffic is encrypted end-to-end
The no-authentication limitation of this project is much less risky when using Tailscale, because only your own trusted devices can reach the server in the first place.
