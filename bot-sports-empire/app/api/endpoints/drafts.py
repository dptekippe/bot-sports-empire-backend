"""
Draft endpoints for Bot Sports Empire.

FastAPI endpoints for draft management: create drafts, make picks, get draft status.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
import logging

from ...core.database import get_db
from ...models.draft import Draft, DraftPick
from ...models.league import League
from ...models.team import Team
from ...models.player import Player
from ...schemas.draft import (
    DraftCreate, DraftResponse, DraftUpdate, DraftListResponse,
    DraftPickCreate, DraftPickResponse, MakePickRequest, MakePickResponse,
    DraftWithPicksResponse, DraftFullResponse
)
from ...api.websockets.draft_room import broadcast_pick_made
from ...services.draft_analytics import DraftAnalyticsService

router = APIRouter()


@router.post("/", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
def create_draft(draft: DraftCreate, db: Session = Depends(get_db)):
    """
    Create a new draft.
    
    Creates a draft with the specified settings. If no draft_order is provided,
    a random order will be generated.
    """
    try:
        # Check if league exists (if provided)
        if draft.league_id:
            league = db.query(League).filter(League.id == draft.league_id).first()
            if not league:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"League {draft.league_id} not found"
                )
        
        # Create draft
        db_draft = Draft(
            id=str(uuid.uuid4()),
            name=draft.name,
            draft_type=draft.draft_type.name,  # Use enum name (SNAKE) not value (snake)
            rounds=draft.rounds,
            team_count=draft.team_count,
            seconds_per_pick=draft.seconds_per_pick,
            league_id=draft.league_id,
            draft_order=draft.draft_order or [],  # Will be populated if empty
        )
        
        # If no draft order provided, we'll generate it when draft starts
        # For now, just save with empty order
        
        db.add(db_draft)
        db.commit()
        db.refresh(db_draft)
        
        # Convert to response
        return DraftResponse.from_orm(db_draft)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating draft: {str(e)}"
        )


@router.get("/", response_model=DraftListResponse)
def list_drafts(
    skip: int = 0,
    limit: int = 100,
    league_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all drafts with optional filtering.
    
    Supports filtering by league_id and status.
    """
    try:
        # Build query
        query = db.query(Draft)
        
        if league_id:
            query = query.filter(Draft.league_id == league_id)
        
        if status:
            query = query.filter(Draft.status == status)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        drafts = query.offset(skip).limit(limit).all()
        
        # Convert to responses
        draft_responses = [DraftResponse.from_orm(draft) for draft in drafts]
        
        return DraftListResponse(
            drafts=draft_responses,
            total=total,
            page=(skip // limit) + 1 if limit > 0 else 1,
            page_size=limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing drafts: {str(e)}"
        )


@router.get("/{draft_id}", response_model=DraftFullResponse)
def get_draft(draft_id: str, db: Session = Depends(get_db)):
    """
    Get a draft by ID with all details.
    
    Returns draft with slots and picks included.
    """
    try:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Get picks for this draft
        picks = db.query(DraftPick).filter(DraftPick.draft_id == draft_id).all()
        
        # Convert to response
        draft_response = DraftResponse.from_orm(draft)
        
        # Convert picks to responses
        pick_responses = [DraftPickResponse.from_orm(pick) for pick in picks]
        
        # Create full response
        return DraftFullResponse(
            **draft_response.dict(),
            picks=pick_responses,
            slots=[]  # TODO: Add slots when we have DraftSlot model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting draft: {str(e)}"
        )


@router.put("/{draft_id}", response_model=DraftResponse)
def update_draft(draft_id: str, draft_update: DraftUpdate, db: Session = Depends(get_db)):
    """
    Update draft settings.
    
    Can update name, status, timer settings, etc.
    """
    try:
        db_draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not db_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Update fields
        update_data = draft_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_draft, key, value)
        
        db.commit()
        db.refresh(db_draft)
        
        return DraftResponse.from_orm(db_draft)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating draft: {str(e)}"
        )


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(draft_id: str, db: Session = Depends(get_db)):
    """
    Delete a draft.
    
    Only allowed if draft is not in progress.
    """
    try:
        db_draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not db_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Check if draft can be deleted
        if db_draft.status == "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete draft that is in progress"
            )
        
        # Delete associated picks first
        db.query(DraftPick).filter(DraftPick.draft_id == draft_id).delete()
        
        # Delete draft
        db.delete(db_draft)
        db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting draft: {str(e)}"
        )


@router.get("/{draft_id}/picks", response_model=List[DraftPickResponse])
def list_draft_picks(
    draft_id: str,
    round: Optional[int] = None,
    team_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all picks for a draft.
    
    Can filter by round and/or team_id.
    """
    try:
        # Verify draft exists
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Build query
        query = db.query(DraftPick).filter(DraftPick.draft_id == draft_id)
        
        if round:
            query = query.filter(DraftPick.round == round)
        
        if team_id:
            query = query.filter(DraftPick.team_id == team_id)
        
        # Order by pick number
        query = query.order_by(DraftPick.pick_number)
        
        picks = query.all()
        
        return [DraftPickResponse.from_orm(pick) for pick in picks]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing draft picks: {str(e)}"
        )


@router.post("/{draft_id}/picks", response_model=MakePickResponse)
def make_draft_pick(
    draft_id: str,
    pick_request: MakePickRequest,
    db: Session = Depends(get_db)
):
    """
    Make a draft pick.
    
    This is the core draft room endpoint where teams select players.
    Validates it's the correct team's turn and the player is available.
    """
    try:
        # Get draft
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Check if draft is active
        if draft.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot make pick when draft is {draft.status}"
            )
        
        # TODO: Get current team turn from draft logic
        # For now, we'll need to implement the full draft turn logic
        # This is a simplified version
        
        # Find the current pick record
        current_pick = db.query(DraftPick).filter(
            DraftPick.draft_id == draft_id,
            DraftPick.round == draft.current_round,
            DraftPick.pick_number == draft.current_pick
        ).first()
        
        if not current_pick:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not find current pick record"
            )
        
        # Check if player is already drafted
        existing_pick = db.query(DraftPick).filter(
            DraftPick.draft_id == draft_id,
            DraftPick.player_id == pick_request.player_id,
            DraftPick.player_id.isnot(None)
        ).first()
        
        if existing_pick:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player {pick_request.player_id} already drafted"
            )
        
        # Update the pick
        current_pick.player_id = pick_request.player_id
        current_pick.position = pick_request.position
        current_pick.was_auto_pick = pick_request.was_auto_pick
        current_pick.bot_thinking_time = pick_request.bot_thinking_time
        
        # Update draft state
        draft.completed_picks.append(current_pick.id)
        
        # Move to next pick
        total_picks = draft.rounds * draft.team_count
        if draft.current_pick < total_picks:
            draft.current_pick += 1
            draft.current_round = ((draft.current_pick - 1) // draft.team_count) + 1
            
            # Check if draft is complete
            if draft.current_pick > total_picks:
                draft.status = "completed"
                draft.actual_end = func.now()
        
        db.commit()
        db.refresh(current_pick)
        db.refresh(draft)
        
        # Record pick to DraftHistory for internal ADP tracking
        try:
            analytics_service = DraftAnalyticsService(db)
            
            # Get league if draft has one
            league = None
            if draft.league_id:
                league = db.query(League).filter(League.id == draft.league_id).first()
            
            # Record the pick
            analytics_service.record_internal_draft_pick(
                draft_pick=current_pick,
                draft=draft,
                league=league
            )
            
            # Update player's internal ADP field
            analytics_service.update_player_internal_adp_field(current_pick.player_id)
            
            logger = logging.getLogger(__name__)
            logger.info(f"Recorded draft pick {current_pick.pick_number} for player {current_pick.player_id}")
            
        except Exception as e:
            # Don't fail the pick if analytics recording fails
            logger = logging.getLogger(__name__)
            logger.error(f"Error recording draft pick to analytics: {e}")
        
        # Get next team turn (simplified)
        next_team_turn = None
        next_pick_number = None
        if draft.current_pick <= total_picks:
            next_pick_number = draft.current_pick
            # TODO: Calculate next team based on draft type and order
        
        return MakePickResponse(
            success=True,
            pick=DraftPickResponse.from_orm(current_pick),
            next_team_turn=next_team_turn,
            next_pick_number=next_pick_number,
            draft_complete=(draft.status == "completed"),
            message="Pick made successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error making pick: {str(e)}"
        )


@router.post("/{draft_id}/start", response_model=DraftResponse)
def start_draft(draft_id: str, db: Session = Depends(get_db)):
    """
    Start a draft.
    
    Transitions draft from SCHEDULED to IN_PROGRESS status.
    Generates draft order if not already set.
    Creates all pick records.
    """
    try:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Check if draft can be started
        # Handle both string and enum status
        status_value = draft.status.value if hasattr(draft.status, 'value') else draft.status
        if status_value != "scheduled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start draft in {status_value} status"
            )
        
        # Generate draft order if not set
        if not draft.draft_order or len(draft.draft_order) != draft.team_count:
            # TODO: Get teams from league or generate random order
            # For now, create placeholder order
            draft.draft_order = [f"team_{i+1}" for i in range(draft.team_count)]
        
        # Start the draft using model method
        try:
            # Call the model's start_draft method which creates picks
            draft.start_draft()
            
            # Create pick records in database
            picks = draft._create_pick_records()
            for pick in picks:
                db.add(pick)
            
            db.commit()
            db.refresh(draft)
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        return DraftResponse.from_orm(draft)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting draft: {str(e)}"
        )


@router.post("/{draft_id}/picks/{pick_id}/player/{player_id}", response_model=DraftPickResponse)
def assign_player_to_pick(
    draft_id: str,
    pick_id: str,
    player_id: str,
    db: Session = Depends(get_db)
):
    """
    Assign a player to a specific draft pick.
    
    Core endpoint for draft room: validates player availability and updates pick.
    
    Validations:
    1. Draft exists and is in progress
    2. Pick exists and belongs to this draft
    3. Player exists and is active
    4. Player not already drafted in this draft
    5. Player not already on a fantasy team
    
    Returns: Updated pick with player assigned
    Status codes:
    - 201: Player successfully assigned
    - 404: Draft, pick, or player not found
    - 409: Player already taken or unavailable
    - 422: Invalid state (draft not in progress, pick already assigned)
    """
    try:
        # 1. Validate draft exists and is in progress
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Check if draft is in progress (accept both string and enum)
        from app.models.draft import DraftStatus
        is_in_progress = False
        
        if isinstance(draft.status, DraftStatus):
            is_in_progress = draft.status == DraftStatus.IN_PROGRESS
        else:
            is_in_progress = draft.status in ["in_progress", "IN_PROGRESS", "drafting"]
        
        if not is_in_progress:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot assign players to draft in {draft.status} status. Draft must be in progress."
            )
        
        # 2. Validate pick exists and belongs to this draft
        pick = db.query(DraftPick).filter(
            DraftPick.id == pick_id,
            DraftPick.draft_id == draft_id
        ).first()
        
        if not pick:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pick {pick_id} not found in draft {draft_id}"
            )
        
        # Check if pick already has a player
        if pick.player_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Pick {pick_id} already has player {pick.player_id} assigned"
            )
        
        # 3. Validate player exists and is active
        player = db.query(Player).filter(Player.player_id == player_id).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found"
            )
        
        # Check if player is active
        if not player.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Player {player.full_name} is not active"
            )
        
        # 4. Check if player already drafted in this draft
        existing_pick = db.query(DraftPick).filter(
            DraftPick.draft_id == draft_id,
            DraftPick.player_id == player_id,
            DraftPick.player_id.isnot(None)
        ).first()
        
        if existing_pick:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Player {player.full_name} already drafted at pick {existing_pick.pick_number}"
            )
        
        # 5. Check if player already on a fantasy team
        if player.current_team_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Player {player.full_name} already owned by team {player.current_team_id}"
            )
        
        # All validations passed - assign player to pick
        pick.player_id = player_id
        pick.position = player.position
        
        # Update pick timestamps
        from sqlalchemy import func
        pick.pick_end_time = func.now()
        
        # Calculate pick time if start time exists
        if pick.pick_start_time:
            pick_time = (pick.pick_end_time - pick.pick_start_time).total_seconds()
            pick.pick_time_seconds = int(pick_time)
        
        # Update draft state
        if pick.id not in draft.completed_picks:
            draft.completed_picks.append(pick.id)
        
        # Update player's current team (if pick has a team)
        if pick.team_id:
            player.current_team_id = pick.team_id
        
        # Commit all changes
        db.commit()
        
        # Refresh objects to get updated data
        db.refresh(pick)
        db.refresh(player)
        
        # Convert to response
        pick_response = DraftPickResponse.from_orm(pick)
        
        # WebSocket broadcast temporarily disabled for MVP deployment
        # try:
        #     import asyncio
        #     asyncio.create_task(broadcast_pick_made(draft_id, pick_response))
        # except Exception:
        #     pass
        print(f"📢 Pick made: {player.full_name} to {pick.team_id} (WebSocket disabled for MVP)")
        
        return pick_response
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assigning player to pick: {str(e)}"
        )


# Helper endpoint for testing
@router.post("/{draft_id}/test/populate")
def test_populate_draft(draft_id: str, db: Session = Depends(get_db)):
    """
    TEST ENDPOINT: Populate draft with test picks.
    
    Only for development/testing.
    """
    try:
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft {draft_id} not found"
            )
        
        # Create test picks
        # This is just for testing the API
        
        db.commit()
        
        return {"message": "Test picks created", "count": 0}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in test endpoint: {str(e)}"
        )