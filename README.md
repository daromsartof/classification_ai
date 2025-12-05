# AI Separation Python Application

## Docker Usage

### 1. Build the Docker Image (Standalone)
```sh
docker build -t ai-separation-app .
```

### 2. Run the Docker Container (Standalone)
Set the required environment variables (see below) and mount any necessary volumes for input/output if needed.

```sh
docker run --rm \
  -e OPENAI_API_KEY=your_openai_key \
  -e DB_HOST=your_db_host \
  -e DB_USER=your_db_user \
  -e DB_PASSWORD=your_db_password \
  -e DB_DATABASE=your_db_name \
  -e GOOGLE_PROJECT_ID=your_project_id \
  -e GOOGLE_LOCATION=your_location \
  -e GOOGLE_PROCESSOR_ID=your_processor_id \
  -e IMAGE_BASE=/mnt/images \
  -e IMAGE_A_TRAITER=/mnt/images_a_traiter \
  -v /path/to/your/images:/mnt/images \
  -v /path/to/your/images_a_traiter:/mnt/images_a_traiter \
  ai-separation-app
```

---

## Docker Compose Usage

### 1. Prepare the `.env` file
Copy the following template to a file named `.env` in the project root and fill in your values:

```
OPENAI_API_KEY=your_openai_key
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_DATABASE=your_db_name
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_LOCATION=your_location
GOOGLE_PROCESSOR_ID=your_processor_id
```

### 2. Mount NAS Shares on Host
Ensure your NAS directories are mounted on your host system. For example:
- `/mnt/nas/images` → maps to your NAS `IMAGES_V2/images`
- `/mnt/nas/images_a_traiter` → maps to your NAS `IMAGES_A_TRAITER`

Update the `docker-compose.yml` file if your mount points differ.

### 3. Start the Application
```sh
docker-compose up --build
```

This will:
- Build the Docker image
- Start the app with environment variables from `.env`
- Mount the NAS shares and credentials file into the container

---

## Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE`: MySQL database connection
- `GOOGLE_PROJECT_ID`, `GOOGLE_LOCATION`, `GOOGLE_PROCESSOR_ID`: Google Document AI configuration
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to the Google service account JSON (default: `/app/credential.json`)
- `IMAGE_BASE`: Path for output images (default: `/mnt/images`)
- `IMAGE_A_TRAITER`: Path for input images (default: `/mnt/images_a_traiter`)

---

## Notes
- Make sure to provide the correct paths for your images and credentials.
- You may need to adjust volume mounts and environment variables to fit your deployment.
- If you need to add a database service to `docker-compose.yml`, you can do so as needed. 