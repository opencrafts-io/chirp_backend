import os
import uuid


def get_community_banner_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"banner_{uuid.uuid4().hex}.{ext}"
    return os.path.join("communities", str(instance.name), "banners", filename)


def get_community_profile_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"profile_{uuid.uuid4().hex}.{ext}"
    return os.path.join("communities", str(instance.name), "profiles", filename)
