import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="VibeChat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Helpers ----------

def oid_str(value):
    if isinstance(value, ObjectId):
        return str(value)
    return value


def serialize(doc):
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = oid_str(v)
        elif isinstance(v, ObjectId):
            out[k] = oid_str(v)
        else:
            out[k] = v
    return out


# ---------- Request Models ----------

class CreateUser(BaseModel):
    name: str
    avatar: Optional[str] = None
    status: Optional[str] = "Hey there! I am using VibeChat"


class CreateChat(BaseModel):
    participants: List[str] = Field(..., description="List of user IDs")
    title: Optional[str] = None
    is_group: bool = False


class CreateMessage(BaseModel):
    chat_id: str
    sender_id: str
    content: str
    type: str = "text"


# ---------- Root & Health ----------

@app.get("/")
def read_root():
    return {"message": "VibeChat Backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# ---------- Users ----------

@app.get("/api/users")
def list_users(q: Optional[str] = Query(None, description="Search by name contains")):
    filter_dict = {}
    if q:
        filter_dict = {"name": {"$regex": q, "$options": "i"}}
    docs = get_documents("user", filter_dict)
    return [serialize(d) for d in docs]


@app.post("/api/users")
def create_user(payload: CreateUser):
    user_id = create_document("user", payload.model_dump())
    doc = db["user"].find_one({"_id": ObjectId(user_id)})
    return serialize(doc)


# ---------- Chats ----------

@app.get("/api/chats")
def list_chats(user_id: str = Query(..., description="User ID to list chats for")):
    # Find chats where user_id is in participants
    docs = get_documents("chat", {"participants": user_id})
    # Sort by updated_at descending
    docs = sorted(docs, key=lambda d: d.get("updated_at"), reverse=True)
    return [serialize(d) for d in docs]


@app.post("/api/chats")
def create_chat(payload: CreateChat):
    if len(payload.participants) < 2 and not payload.is_group:
        raise HTTPException(status_code=400, detail="A direct chat requires 2 participants")
    chat_id = create_document("chat", payload.model_dump())
    doc = db["chat"].find_one({"_id": ObjectId(chat_id)})
    return serialize(doc)


# ---------- Messages ----------

@app.get("/api/messages")
def list_messages(chat_id: str = Query(...)):
    docs = get_documents("message", {"chat_id": chat_id})
    # Sort by created_at ascending for chat history
    docs = sorted(docs, key=lambda d: d.get("created_at"))
    return [serialize(d) for d in docs]


@app.post("/api/messages")
def send_message(payload: CreateMessage):
    # Ensure chat exists
    chat = db["chat"].find_one({"_id": ObjectId(payload.chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    # Ensure sender is in chat participants
    if payload.sender_id not in chat.get("participants", []):
        raise HTTPException(status_code=403, detail="Sender not part of this chat")

    msg_id = create_document("message", payload.model_dump())
    # Update chat updated_at for sorting
    db["chat"].update_one({"_id": chat["_id"]}, {"$set": {"updated_at": db["message"].find_one({"_id": ObjectId(msg_id)})["created_at"]}})

    doc = db["message"].find_one({"_id": ObjectId(msg_id)})
    return serialize(doc)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
