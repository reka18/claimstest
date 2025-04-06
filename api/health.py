from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify service availability.

    This endpoint can be used by monitoring systems, load balancers,
    or deployment tools to verify that the service is running and responsive.

    Returns:
        dict: A simple response indicating service health.
              Example: {"message": "OK"}
    """
    return {"message": "OK"}