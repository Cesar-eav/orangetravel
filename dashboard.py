from django.utils.translation import gettext_lazy as _
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard, AppIndexDashboard
from unfold.admin import ModelAdmin

class CustomIndexDashboard(Dashboard):
    def init_with_context(self, context):
        # 1. ENLACES RÁPIDOS (Lo que ya tienes)
        self.children.append(modules.LinkList(
            _('Enlaces rápidos'),
            layout='inline',
            children=[
                [_('Volver al sitio'), '/'],
                [_('Cambiar contraseña'), 'admin:password_change'],
                [_('Cerrar sesión'), 'admin:logout'],
            ],
            column=0,
            order=0
        ))

        # 2. APLICACIONES (Tours, Usuarios, etc.)
        self.children.append(modules.AppList(
            _('Aplicaciones y Módulos'),
            column=1,
            order=0
        ))

        # 3. ACCIONES RECIENTES (Lo que has estado editando)
        self.children.append(modules.RecentActions(
            _('Acciones recientes'),
            column=0,
            order=1,
            limit=5
        ))

# Esto asegura que dentro de cada App también se vea bien
class CustomAppIndexDashboard(AppIndexDashboard):
    def init_with_context(self, context):
        self.children.append(modules.ModelList(
            _('Modelos del sistema'),
            context['app_label'],
            column=0,
            order=0
        ))