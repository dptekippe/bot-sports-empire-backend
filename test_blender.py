import asyncio
import sys
sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')
from app.services.value_blender_v2 import ValueBlenderService

async def test():
    service = ValueBlenderService()
    await service.initialize()
    
    # Test Josh Allen
    josh = await service.blend_player('Josh Allen')
    print(f'Josh Allen: consensus={josh.consensus}, sources={josh.sources_used}, breakdown={josh.breakdown}')
    
    # Test Bijan Robinson
    bijan = await service.blend_player('Bijan Robinson')
    print(f'Bijan Robinson: consensus={bijan.consensus}, sources={bijan.sources_used}, breakdown={bijan.breakdown}')
    
    # Summary
    print(f'Summary: {service.get_blend_summary()}')

asyncio.run(test())
