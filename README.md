# Agents-for-information-extraction--
Specialized agents for visual understanding

# 📄 VRDU Pro Agent: AI-Powered Document Extraction
An end-to-end Visual Document Understanding (VRDU) agent built with FastAPI, Tesseract OCR, and NetworkX. This agent doesn't just "read" text; it understands the spatial layout of documents to extract structured data from invoices, forms, and tables with high precision.


# Pipeline
The agent follows a multi-stage Visual Document Understanding (VRDU) pipeline to ensure high accuracy even with complex layouts:

**1. Vision & Pre-processing**

***PDF to Image:*** Converts document pages into high-resolution images using pdf2image.

***Memory Optimization:*** Downscales to 120 DPI and converts to Grayscale to stay within a 512MB RAM footprint.

***Normalization:*** Applies Autocontrast to improve OCR legibility on faded documents.

**2. Spatial Intelligence (OCR & Geometry)**

***Geometry Extraction:*** Uses Tesseract to get (x, y, w, h) coordinates for every word.

***Graph Reasoning:*** Builds a Directed Acyclic Graph (DAG) where nodes are words and edges represent "above/below" or "left/right" relationships.

***Topological Sort:*** Determines the Human Reading Order, preventing the "column-mixing" error common in standard PDF readers.

**3. Data Extraction & Heuristics**

***Radial Anchor Search:*** Locates a "Target Label" (e.g., Total) and searches in a 2D radius to find the corresponding value.

***Grid Detection:*** Identifies rows and columns by analyzing the Y-axis alignment of text elements to reconstruct tables.

**4. Validation & Delivery**

***Regex Filtering:*** Uses pattern matching to ensure "Dates" look like dates and "Totals" look like currency.

***Asynchronous Polling:*** Jobs are processed in a background thread; results are cached and retrieved via a unique job_id.

# 🚀 Key Features
Sequential Page Processing: Optimized for low-memory environments (runs on 512MB RAM).

Spatial Graph Reasoning: Uses Directed Acyclic Graphs (DAG) to determine human-like reading order.

Radial Anchor Search: Intelligently finds values located to the right or below labels.

Async Task Queue: Handles long documents in the background to prevent API timeouts.

Validation Layer: Self-correcting logic for common OCR errors using Regex.

# 🛠️ Tech Stack
Language: Python 3.10

API Framework: FastAPI (Asynchronous)

OCR Engine: Tesseract OCR

Computer Vision: Pillow & pdf2image

Graph Theory: NetworkX (Topological Sorting)

***Deployment: Docker & Render***

# 📦 Local Setup
**1. Prerequisites**
Install Tesseract OCR on your system.

Install Poppler (required for pdf2image).

**2. Installation**

```Bash```

```
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
pip install -r requirements.txt
```

**3. Running the Agent**

```Bash```

```
uvicorn agent_service:app --reload
Access the interactive API docs at:  http://localhost:8000/docs.

```

# 🐳 Docker Setup

To run the agent in a containerized environment (exactly like the cloud):

```Bash```

```
docker build -t vrdu-agent .
docker run -p 8000:8000 vrdu-agent
```

# 🚦 API Usage

**1. Start a Job (POST /process)**

Upload a PDF and specify which fields you want to extract.

Body: file (PDF), fields (e.g., "Total, Date, Invoice")

```
Response: Returns a job_id.

```

**2. Get Results (GET /results/{job_id})**

Check the status of your extraction.

```
Status: processing: Still working.
```

```
Status: completed: Returns structured JSON results.
```

**🧠 Memory Management (Render Optimization)**

This agent is specifically tuned for Render's Free Tier (512MB RAM):

DPI Scaling: Operates at 120 DPI to balance OCR accuracy and memory footprint.

Garbage Collection: Explicitly clears image memory after every page processing cycle.

Grayscale Conversion: Reduces memory usage by 66% during the OCR stage.
