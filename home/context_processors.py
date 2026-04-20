from tours.models import Tour

def footer_tours(request):
    tours = Tour.objects.filter(activo=True).select_related('precio')
    return {'footer_tours': tours}
