from utils.common_utils import SIZE_LABELS
from .models import Size

def get_size_list():
    return [
        {"size_code": size.code, "display_text": SIZE_LABELS.get(size.code, str(size.code))}
        for size in Size.objects.filter(is_active=True)
    ]