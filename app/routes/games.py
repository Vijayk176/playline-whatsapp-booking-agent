from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import GamingOption
from app.schemas.schemas import GamingOptionIn, GamingOptionOut
from app.services.auth_service import get_current_admin

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("", response_model=list[GamingOptionOut])
def list_games(db: Session = Depends(get_db)):
    return db.query(GamingOption).order_by(GamingOption.id).all()


@router.post("", response_model=GamingOptionOut)
def create_game(data: GamingOptionIn, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    game = GamingOption(**data.model_dump())
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@router.put("/{game_id}", response_model=GamingOptionOut)
def update_game(game_id: int, data: GamingOptionIn, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    game = db.query(GamingOption).filter(GamingOption.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Gaming option not found")
    for k, v in data.model_dump().items():
        setattr(game, k, v)
    db.commit()
    db.refresh(game)
    return game


@router.delete("/{game_id}")
def deactivate_game(game_id: int, db: Session = Depends(get_db), _admin: str = Depends(get_current_admin)):
    game = db.query(GamingOption).filter(GamingOption.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Gaming option not found")
    game.active = False
    db.commit()
    return {"status": "deactivated"}
