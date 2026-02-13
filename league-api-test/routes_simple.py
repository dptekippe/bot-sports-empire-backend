"""
Simple league routes for standalone test
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Local imports
from database import get_db
from models import League, Bot
from schemas import (
    LeagueCreateRequest, 
    LeagueCreateResponse, 
    LeagueResponse,
    ErrorResponse,
    VALIDATION_ERRORS
)
from auth import get_current_bot, get_bot_info

router = APIRouter(prefix="/api/v1/leagues", tags=["leagues"])

@router.post(
    "",
    response_model=LeagueCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "League created successfully"},
        400: {"model": ErrorResponse, "description": "Bad request - validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid API key"},
        409: {"model": ErrorResponse, "description": "Conflict - league name already exists"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity - validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_league(
    league_data: LeagueCreateRequest,
    bot: Bot = Depends(get_current_bot),
    db: Session = Depends(get_db)
):
    """
    Create a new fantasy/dynasty league
    """
    try:
        # Check if league name already exists (case-insensitive)
        existing_league = db.query(League).filter(
            League.name.ilike(league_data.name)
        ).first()
        
        if existing_league:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"League name '{league_data.name}' already exists. Please choose a different name."
            )
        
        # Create new league
        new_league = League(
            name=league_data.name,
            format=league_data.format.value,
            attribute=league_data.attribute.value,
            creator_bot_id=bot.id,
            status="forming",
            team_count=12,
            visibility="public"
        )
        
        # Add to database
        db.add(new_league)
        db.commit()
        db.refresh(new_league)
        
        # Get updated bot info with new league
        db.refresh(bot)
        
        # Prepare response
        response = LeagueCreateResponse(
            message="🎉 League created successfully!",
            league=LeagueResponse.from_orm(new_league),
            bot_info=get_bot_info(bot)
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Database integrity error: {str(e)}"
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get(
    "",
    response_model=list[LeagueResponse],
    responses={
        200: {"description": "List of all leagues"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid API key"}
    }
)
async def list_leagues(
    bot: Bot = Depends(get_current_bot),
    db: Session = Depends(get_db)
):
    """
    List all leagues in the system
    """
    try:
        leagues = db.query(League).filter(
            League.status == "forming"
        ).order_by(League.created_at.desc()).all()
        
        return [LeagueResponse.from_orm(league) for league in leagues]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching leagues: {str(e)}"
        )

@router.get(
    "/my-leagues",
    response_model=list[LeagueResponse],
    responses={
        200: {"description": "List of leagues created by the authenticated bot"},
        401: {"model": ErrorResponse, "description": "Unauthorized - invalid API key"}
    }
)
async def get_my_leagues(
    bot: Bot = Depends(get_current_bot),
    db: Session = Depends(get_db)
):
    """
    Get leagues created by the authenticated bot
    """
    try:
        # Bot leagues are already loaded via relationship
        return [LeagueResponse.from_orm(league) for league in bot.leagues]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching your leagues: {str(e)}"
        )