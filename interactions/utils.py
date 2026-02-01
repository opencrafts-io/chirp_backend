from django.db.models import Q
from .models import Block

def get_mutual_blocked_ids(user):
    """
    Returns a set of User IDs that have a mutual block relationship 
    with the provided user.
    """
    
    blocked_relations = Block.objects.filter(
        Q(blocker=user, block_type='user') | 
        Q(blocked_user=user, block_type='user')
    )
    
    blocked_ids = set()
    for b in blocked_relations:
        if b.blocker_id != user.user_id: 
            blocked_ids.add(b.blocker_id)
        if b.blocked_user_id and b.blocked_user_id != user.user_id: 
            blocked_ids.add(b.blocked_user_id)
            
    return list(blocked_ids)