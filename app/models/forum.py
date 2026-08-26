import datetime
from app.extensions import db
from mongoengine import CASCADE

class ForumPost(db.Document):
    meta = {
        'collection': 'forum_posts',
        'ordering': ['-created_at'],
        'strict': False
    }

    title = db.StringField(required=True)
    content = db.StringField(required=True)
    author = db.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    category_tag = db.StringField(required=True, default='General Advice')
    
    view_count = db.IntField(default=0)
    # ADD THIS NEW FIELD:
    viewed_by = db.ListField(db.ReferenceField('User'), default=list)
    
    upvotes = db.ListField(db.ReferenceField('User'), default=list)
    bookmarks = db.ListField(db.ReferenceField('User'), default=list)
    comment_count = db.IntField(default=0)
    embedding = db.ListField(db.FloatField(), default=list)
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.datetime.utcnow)

class ForumComment(db.Document):
    meta = {
        'collection': 'forum_comments',
        'ordering': ['created_at'],
        'strict': False
    }

    post = db.ReferenceField('ForumPost', required=True, reverse_delete_rule=CASCADE)
    author = db.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    content = db.StringField(required=True)
    upvotes = db.ListField(db.ReferenceField('User'), default=list)
    
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)