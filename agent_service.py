import os
import re
import uuid
import json
import datetime
import shutil
import networkx as nx
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
import uvicorn
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageOps

# ==========================================
# 1. THE CORE VRDU AGENT LOGIC
# ==========================================
class VRDUAgent:
    def __init__(self):
        self.name = "VRDU_Pro_Agent_Integrated"
        self.version = "1.2.0"

    def process_document(self, pdf_path: str, target_fields: List[str]) -> Dict[str, Any]:
        """The 11-Stage Pipeline as defined in our architecture."""
        start_time = datetime.datetime.now()
        
        # STAGE 1: Preprocess
        images = convert_from_path(pdf_path, dpi=300)
        full_results = []

        for i, img in enumerate(images):
            page_num = i + 1
            # Image Normalization
            img = ImageOps.grayscale(img)
            img = ImageOps.autocontrast(img)

            # STAGE 2 & 3: Extraction (OCR + Geometry)
            raw_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            elements = self._clean_ocr_data(raw_data, page_num)

            # STAGE 4: Reading Order (Topological Sort)
            sequence = self._determine_reading_order(elements)
            elements_map = {el['id']: el for el in elements}
            ordered_elements = [elements_map[eid] for eid in sequence]

            # STAGE 8 & 10: Advanced Radial Anchor Search
            fields = self._extract_anchored_fields(ordered_elements, target_fields)
            
            # STAGE 11: Validation & Cleaning
            validated_fields = self._validate_and_clean(fields)

            # STAGE 9: Table/Grid Extraction
            table = self._extract_table_grid(ordered_elements)

            full_results.append({
                "page": page_num,
                "fields": validated_fields,
                "table": table,
                "raw_text": " ".join([el['text'] for el in ordered_elements])
            })

        duration = (datetime.datetime.now() - start_time).total_seconds()
        return {
            "metadata": {"time_sec": duration, "pages": len(images), "agent": self.name},
            "data": full_results
        }

    def _clean_ocr_data(self, data, page_num):
        elements = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if text and int(data['conf'][i]) > 40:
                elements.append({
                    "id": f"p{page_num}_e{i}",
                    "text": text,
                    "bbox": [data['left'][i], data['top'][i], data['left'][i] + data['width'][i], data['top'][i] + data['height'][i]],
                    "center": [data['left'][i] + (data['width'][i]/2), data['top'][i] + (data['height'][i]/2)]
                })
        return elements

    def _determine_reading_order(self, elements):
        G = nx.DiGraph()
        for i, e1 in enumerate(elements):
            G.add_node(e1['id'])
            for j, e2 in enumerate(elements):
                if i == j: continue
                if e1['bbox'][3] < e2['bbox'][1] - 5: # Above
                    G.add_edge(e1['id'], e2['id'])
                elif abs(e1['center'][1] - e2['center'][1]) < 10: # Same line
                    if e1['bbox'][2] < e2['bbox'][0]: # Left
                        G.add_edge(e1['id'], e2['id'])
        try:
            return list(nx.topological_sort(G))
        except:
            return [e['id'] for e in sorted(elements, key=lambda x: (x['bbox'][1], x['bbox'][0]))]

    def _extract_anchored_fields(self, elements, targets):
        found = {}
        for target in targets:
            anchor = next((el for el in elements if target.lower() in el['text'].lower()), None)
            if anchor:
                candidates = []
                for el in elements:
                    if el['id'] == anchor['id']: continue
                    dx = el['bbox'][0] - anchor['bbox'][2]
                    dy = el['bbox'][1] - anchor['bbox'][3]
                    # Right Search
                    if 0 < dx < 250 and abs(el['center'][1] - anchor['center'][1]) < 20:
                        candidates.append({"text": el['text'], "dist": dx})
                    # Below Search
                    elif 0 < dy < 80 and abs(el['center'][0] - anchor['center'][0]) < 60:
                        candidates.append({"text": el['text'], "dist": dy})
                
                if candidates:
                    candidates.sort(key=lambda x: x['dist'])
                    found[target] = candidates[0]['text']
        return found

    def _validate_and_clean(self, fields):
        rules = {"Total": r"\d+[.,]\d{2}", "Date": r"\d+[-/.]\d+[-/.]\d+"}
        results = {}
        for k, v in fields.items():
            clean_v = v.replace('S', '$').replace('O', '0')
            match = re.search(rules.get(k, r".*"), clean_v)
            results[k] = {"value": clean_v, "valid": bool(match)}
        return results

    def _extract_table_grid(self, elements):
        if not elements: return []
        rows = []
        current_row = [elements[0]]
        for i in range(1, len(elements)):
            if abs(elements[i]['center'][1] - current_row[-1]['center'][1]) < 12:
                current_row.append(elements[i])
            else:
                if len(current_row) >= 3: # Table heuristic
                    rows.append([el['text'] for el in sorted(current_row, key=lambda x: x['bbox'][0])])
                current_row = [elements[i]]
        return rows

# ==========================================
# 2. FASTAPI ASYNC MICROSERVICE WRAPPER
# ==========================================
app = FastAPI(title="Pro VRDU Agent API")
agent = VRDUAgent()
results_db = {} # In-memory storage (Use Redis for production)

def background_processing(job_id: str, file_path: str, fields: List[str]):
    try:
        results_db[job_id]["status"] = "processing"
        output = agent.process_document(file_path, fields)
        results_db[job_id].update({"status": "completed", "result": output})
    except Exception as e:
        results_db[job_id].update({"status": "failed", "error": str(e)})
    finally:
        if os.path.exists(file_path): os.remove(file_path)

@app.post("/process")
async def process_pdf(bt: BackgroundTasks, file: UploadFile = File(...), fields: str = Form(...)):
    job_id = str(uuid.uuid4())
    file_path = f"tmp_{job_id}.pdf"
    with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
    
    field_list = [f.strip() for f in fields.split(",")]
    results_db[job_id] = {"status": "queued", "result": None}
    bt.add_task(background_processing, job_id, file_path, field_list)
    
    return {"job_id": job_id, "poll_url": f"/results/{job_id}"}

@app.get("/results/{job_id}")
async def get_results(job_id: str):
    if job_id not in results_db: raise HTTPException(status_code=404)
    return results_db[job_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
