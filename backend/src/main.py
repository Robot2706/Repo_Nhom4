from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import os
import logging

# import module recommender bạn đã tạo
from services import recommender as recmod

app = FastAPI(title="Hotel Recommender POC", version="0.1")

# --- CORS (cho frontend local/dev) ---
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recommender-api")

# --- Pydantic models (request / response) ---
class SearchRequest(BaseModel):
    district: str = Field(...)
    budget_min: float = Field(..., ge=0)
    budget_max: float = Field(..., ge=0)
    purpose: str = Field(...)
    check_in: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    check_out: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    topN: Optional[int] = Field(5, ge=1, le=20)

    @field_validator("district", "purpose", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("budget_max")
    @classmethod
    def check_budget(cls, v, info):
        if "budget_min" in info.data and v < info.data["budget_min"]:
            raise ValueError("budget_max must be >= budget_min")
        return v

    @field_validator("check_out")
    @classmethod
    def check_dates(cls, v, info):
        # basic check: we assume valid format thanks to regex; ensure check_out >= check_in
        from datetime import datetime
        if "check_in" in info.data:
            ci = datetime.strptime(info.data["check_in"], "%Y-%m-%d")
            co = datetime.strptime(v, "%Y-%m-%d")
            if co < ci:
                raise ValueError("check_out must be >= check_in")
        return v

class HotelOut(BaseModel):
    id: int
    name: str
    district: str
    price: float
    rating: float
    amenities: List[str]
    score: Optional[float] = None

class RecommendResponse(BaseModel):
    results: List[HotelOut]
    meta: dict

# --- In-memory data load (mock DB). Replace with real repository later ---
DATA_SOURCE = os.getenv("DATA_SOURCE", "mock")  # "mock" | "json" | "sql" | "amadeus"
HOTELS = []

def load_mock_data():
    # use the generator in recommender_module for deterministic test dataset
    global HOTELS
    HOTELS = recmod.generate_mock_hotels(120, seed=42)
    logger.info("Loaded %d mock hotels", len(HOTELS))

# Initialize data on startup
@app.on_event("startup")
def startup_event():
    logger.info("Starting Hotel Recommender API (DATA_SOURCE=%s)", DATA_SOURCE)
    if DATA_SOURCE == "mock":
        load_mock_data()
    else:
        # placeholder for swapping to real data source later
        load_mock_data()
        logger.info("Note: DATA_SOURCE != mock not implemented yet. Using mock data.")

# --- Simple utility endpoints ---
@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/districts", response_model=List[str])
def get_districts():
    # derive districts from loaded data
    districts = sorted({h.district for h in HOTELS})
    return districts

@app.get("/api/hotels/{hotel_id}", response_model=HotelOut)
def get_hotel(hotel_id: int):
    for h in HOTELS:
        if h.id == hotel_id:
            return HotelOut(
                id=h.id,
                name=h.name,
                district=h.district,
                price=h.price,
                rating=h.rating,
                amenities=h.amenities,
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hotel not found")

# --- Main recommend endpoint ---
@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(req: SearchRequest):
    logger.info("Search request: district=%s budget=[%s,%s] purpose=%s topN=%s",
                req.district, req.budget_min, req.budget_max, req.purpose, req.topN)

    # Build UserInput dataclass for recommender module
    top_n = req.topN if req.topN is not None else 5
    user_input = recmod.UserInput(
        district=req.district,
        budget_min=req.budget_min,
        budget_max=req.budget_max,
        purpose=req.purpose,
        check_in=req.check_in,
        check_out=req.check_out,
        topN=top_n,
    )

    # Call search_with_expansion
    results, meta = recmod.search_with_expansion(HOTELS, user_input, topN=top_n)

    if not results:
        # 204 No Content is fine when nothing matches even after expansion
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="no results found")

    # convert to HotelOut list (score already included)
    out_results = []
    for r in results:
        out_results.append(HotelOut(
            id=r["id"],
            name=r["name"],
            district=r["district"],
            price=r["price"],
            rating=r["rating"],
            amenities=r.get("amenities", []),
            score=r.get("score")
        ))

    return RecommendResponse(results=out_results, meta=meta)

# --- Run note ---
# To run locally:
# uvicorn main:app --reload --port 8000
# Make sure recommender_module.py is in the same folder or installed as a package.