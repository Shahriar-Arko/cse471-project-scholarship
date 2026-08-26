import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.forum import ForumPost, ForumComment


forum_bp = Blueprint('forum', __name__, url_prefix='/forum')

@forum_bp.route('/')
@login_required
def forum_home():
    """Renders the main community discussion board."""
    category_filter = request.args.get('category')
    
    if category_filter:
        
        posts = ForumPost.objects(category_tag=category_filter)
    else:
        posts = ForumPost.objects()
        
    return render_template('dashboard/forum.html', posts=posts)



@forum_bp.route('/api/create', methods=['POST'])
@login_required
def api_create_post():
    """Creates a new post instantly without AI processing."""
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    category = data.get('category', 'General Advice').strip()

    if not title or not content:
        return jsonify({'error': 'Title and content are required.'}), 400

#Create the post without the embedding parameter
    post = ForumPost(
        title=title,
        content=content,
        category_tag=category,
        author=current_user.id
    )
    post.save()

    return jsonify({
        'status': 'success', 
        'message': 'Discussion posted successfully!', 
        'post_id': str(post.id)
    })

@forum_bp.route('/post/<post_id>')
@login_required
def view_post(post_id):
    """Renders a single post and its comments, tracking UNIQUE views per user."""
    post = ForumPost.objects(id=post_id).first()
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    # 1. Check if the current user has already viewed this post
    already_viewed = False
    if hasattr(post, 'viewed_by') and post.viewed_by:
        already_viewed = any(str(getattr(u, 'id', u)) == str(current_user.id) for u in post.viewed_by)

    # 2. Only increment the view count if they are a new viewer
    if not already_viewed:
        post.update(push__viewed_by=current_user.id, inc__view_count=1)
        post.reload() # Refresh to get the newly updated count

    # Fetch comments for this post
    comments = ForumComment.objects(post=post.id)
    
    return render_template('dashboard/forum_post.html', post=post, comments=comments)


@forum_bp.route('/api/upvote/<post_id>', methods=['POST'])
@login_required
def toggle_upvote(post_id):
    """Toggles the current user's upvote on a post (strictly max 1 per user)."""
    post = ForumPost.objects(id=post_id).first()
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    # Prevent the author from upvoting their own post
    if str(post.author.id) == str(current_user.id):
        return jsonify({'error': 'You cannot upvote your own post.'}), 403

    # FIX: Safely check if the current user's ID is already in the upvotes list
    has_upvoted = any(str(getattr(u, 'id', u)) == str(current_user.id) for u in post.upvotes)
    
    if has_upvoted:
        # If they already upvoted, clicking again removes their upvote
        post.update(pull__upvotes=current_user.id)
        action = 'removed'
    else:
        # If they haven't upvoted, add it
        post.update(push__upvotes=current_user.id)
        action = 'added'
        
    post.reload()
    return jsonify({'status': 'success', 'action': action, 'upvote_count': len(post.upvotes)})

@forum_bp.route('/api/comment/<post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    post = ForumPost.objects(id=post_id).first()
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    data = request.get_json() or {}
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Comment cannot be empty.'}), 400

    comment = ForumComment(
        post=post.id,
        author=current_user.id,
        content=content
    )
    comment.save()

    # ADD THIS LINE: Increment the comment count on the post
    post.update(inc__comment_count=1)

    return jsonify({'status': 'success', 'message': 'Comment added successfully!'})


@forum_bp.route('/sync-comments')
def sync_comments():
    """Temporary route to fix comment counts on old posts."""
    from app.models.forum import ForumPost, ForumComment
    
    posts = ForumPost.objects()
    for post in posts:
        # Count actual comments in the database for this post
        actual_count = ForumComment.objects(post=post.id).count()
        # Update the post's integer field
        post.update(set__comment_count=actual_count)
        
    return "All post comment counts have been successfully synced! You can go back to the forum."