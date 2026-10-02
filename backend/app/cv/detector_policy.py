"""Explicit scene scope for the measured panoramic person-detector candidate."""


def is_panorama(width, height):
    return width >= 1920 and height > 0 and width / height >= 3


def select_model_weights(settings, video):
    policy = settings.cv_detector_policy
    if policy == "person" or (policy == "auto" and is_panorama(video["width"], video["height"])):
        return settings.person_model_weights, "panoramic_person" if policy == "auto" else "explicit_person"
    return settings.model_weights, "configured_base"
