# app/context_processors.py
from app.models import Post, Tag  # Assuming your models are in app.models
from app import db  # Assuming your db instance is in app.__init__
import sqlalchemy as sa
from flask import current_app  # To access app config for number of items


def inject_sidebar_data():
    """
    Injects data into the template context for the sidebar.
    This includes recent posts and popular tags.
    """
    # --- Recent Posts ---
    # Get the number of recent posts from config, default to 5 for now
    num_recent_posts = current_app.config.get('SIDEBAR_RECENT_POSTS_COUNT', 5)
    try:
        recent_posts = db.session.scalars(
            sa.select(Post).order_by(Post.timestamp.desc()).limit(num_recent_posts)
        ).all()
    except Exception as e:
        # Log the error but don't crash the app if DB query fails during context processing
        current_app.logger.error(f"Error fetching recent posts for sidebar: {e}", exc_info=True)
        recent_posts = []

    # --- Popular Tags ---
    # Get the number of popular tags from config, default to 10
    num_popular_tags = current_app.config.get('SIDEBAR_POPULAR_TAGS_COUNT', 10)
    try:
        # This query gets tags ordered by the number of posts they are associated with.
        # It requires joining Post and Tag through the post_tags association table.
        popular_tags = db.session.scalars(
            sa.select(Tag)
            .join(Post.tags)  # Using the relationship attribute for the join condition
            .group_by(Tag.id)
            .order_by(sa.func.count(Post.id).desc())  # Order by post count
            .limit(num_popular_tags)
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error fetching popular tags for sidebar: {e}", exc_info=True)
        popular_tags = []

    return dict(
        sidebar_recent_posts=recent_posts,
        sidebar_popular_tags=popular_tags
    )
