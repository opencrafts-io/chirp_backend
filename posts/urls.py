from django.urls import path

from posts.views import (
    CommentListCreateView,
    CommentRetrieveView,
    DestroyPostView,
    ListPostView,
    PostCreateView,
    PostSearchView,
    RecordPostViewerView,
    RetrievePostByAuthorView,
    RetrievePostByCommunityView,
    RetrievePostByIDView,
)

# from .views import (
# PostListView,
# PostCreateView,
# PostDetailView,
# CommentCreateView,
# CommentDetailView,
# PostLikeToggleView,
# CommentLikeToggleView,
# GroupPostListView,
# RecommendationMetricsView,
# PostSearchView,
# )

urlpatterns = [
    # path("groups/<int:group_id>/posts/", GroupPostListView.as_view(), name="group-post-list"),
    # path("groups/<int:group_id>/posts/create/", PostCreateView.as_view(), name="group-post-create"),
    #
    path(
        "create",
        PostCreateView.as_view(),
        name="post-create",
    ),
    path(
        "all",
        ListPostView.as_view(),
        name="post-list",
    ),
    path(
        "<int:id>/details",
        RetrievePostByIDView.as_view(),
        name="get-post-by-id",
    ),
    path(
        "by/<uuid:author>",
        RetrievePostByAuthorView.as_view(),
        name="get-post-by-author",
    ),
    path(
        "from/<int:group>",
        RetrievePostByCommunityView.as_view(),
        name="get-post-by-author",
    ),
    path(
        "search",
        PostSearchView.as_view(),
        name="search-for-post",
    ),
    path(
        "<int:id>/delete",
        DestroyPostView.as_view(),
        name="delete-post",
    ),
    # Post view metrics
    path(
        "<int:id>/viewed",
        RecordPostViewerView.as_view(),
        name="record-post-as-viewed",
    ),
    # Comments
    path(
        "<int:post_id>/comments",
        CommentListCreateView.as_view(),
        name="comments-list-create",
    ),
    path(
        "comments/<int:id>/",
        CommentRetrieveView.as_view(),
        name="comment-detail",
    ),

]
