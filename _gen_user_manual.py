"""Generate USER_MANUAL.pdf using fpdf2."""

from fpdf import FPDF
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/arial.ttf"
FONT_BD = "C:/Windows/Fonts/arialbd.ttf"
FONT_I = "C:/Windows/Fonts/ariali.ttf"


class UserManual(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("ArialUni", "", FONT, uni=True)
        self.add_font("ArialUni", "B", FONT_BD, uni=True)
        self.add_font("ArialUni", "I", FONT_I, uni=True)

    def header(self):
        if self.page_no() > 1:
            self.set_font("ArialUni", "I", 8)
            self.cell(0, 5, "DELCA ERP \u2014 Manual de Usuario", align="C")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("ArialUni", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title: str):
        self.set_font("ArialUni", "B", 16)
        self.set_text_color(44, 62, 80)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(52, 152, 219)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def section_title(self, title: str):
        self.set_font("ArialUni", "B", 12)
        self.set_text_color(52, 73, 94)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str):
        self.set_font("ArialUni", "", 10)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet(self, text: str):
        self.set_font("ArialUni", "", 10)
        self.cell(5, 5, "\u2022")
        self.multi_cell(0, 5, text)
        self.ln(1)

    def step(self, num: int, text: str):
        self.set_font("ArialUni", "", 10)
        self.cell(10, 5, f"{num}.")
        self.multi_cell(0, 5, text)
        self.ln(1)


pdf = UserManual()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# --- Title Page ---
pdf.ln(60)
pdf.set_font("ArialUni", "B", 28)
pdf.set_text_color(44, 62, 80)
pdf.cell(0, 15, "DELCA ERP", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("ArialUni", "", 16)
pdf.set_text_color(52, 73, 94)
pdf.cell(0, 12, "Manual de Usuario", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_font("ArialUni", "", 11)
pdf.set_text_color(127, 140, 141)
pdf.cell(0, 8, "Version 1.0.0 - Junio 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "Sistema de Planificacion de Recursos Empresariales", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "DELCA", align="C", new_x="LMARGIN", new_y="NEXT")

# --- Table of Contents ---
pdf.add_page()
pdf.chapter_title("Índice")
toc_items = [
    "1. Introducción",
    "2. Requisitos del Sistema",
    "3. Inicio de Sesión",
    "4. Interfaz Principal",
    "5. Módulo Dashboard",
    "6. Módulo Clientes",
    "7. Módulo Llantas",
    "8. Módulo Facturación",
    "9. Módulo Cartera",
    "10. Módulo Inventario",
    "11. Módulo Backup",
    "12. Cierre de Sesión",
    "13. Solución de Problemas",
]
for item in toc_items:
    pdf.body_text(item)

# --- 1. Introducción ---
pdf.add_page()
pdf.chapter_title("1. Introducción")
pdf.body_text(
    "DELCA ERP es un sistema de planificación de recursos empresariales "
    "diseñado para gestionar las operaciones de DELCA. Este manual le guiará "
    "en el uso diario del sistema, cubriendo desde el inicio de sesión hasta "
    "la operación de cada módulo."
)
pdf.body_text(
    "El sistema está diseñado para ser utilizado por diferentes perfiles de "
    "usuario: Administradores, Gerencia, Operadores y Consulta. Dependiendo "
    "de su rol, verá diferentes opciones en el menú lateral."
)

# --- 2. Requisitos ---
pdf.chapter_title("2. Requisitos del Sistema")
pdf.bullet("Windows 10 u 11 (64 bits)")
pdf.bullet("4 GB de RAM (mínimo)")
pdf.bullet("500 MB de espacio en disco")
pdf.bullet("Resolución de pantalla 1280x720 o superior")
pdf.bullet("No requiere conexión a Internet para operación normal")

# --- 3. Inicio de Sesión ---
pdf.add_page()
pdf.chapter_title("3. Inicio de Sesión")
pdf.section_title("3.1 Acceso al Sistema")
pdf.step(1, "Ejecute DELCA ERP desde el acceso directo del escritorio o menú Inicio.")
pdf.step(2, "En la pantalla de login, ingrese su nombre de usuario.")
pdf.step(3, "Ingrese su contraseña.")
pdf.step(4, "Haga clic en 'Iniciar Sesión'.")

pdf.section_title("3.2 Primer Inicio de Sesión")
pdf.body_text(
    "Si es la primera vez que inicia sesión o si el administrador ha "
    "restablecido su contraseña, el sistema le solicitará cambiar su "
    "contraseña. La nueva contraseña debe cumplir:"
)
pdf.bullet("Mínimo 8 caracteres")
pdf.bullet("Al menos una letra mayúscula")
pdf.bullet("Al menos una letra minúscula")
pdf.bullet("Al menos un número")
pdf.bullet("Al menos un carácter especial (!@#$%^&*(),.?\":{}|<>_-)")

pdf.section_title("3.3 Bloqueo de Cuenta")
pdf.body_text(
    "Después de 5 intentos fallidos de inicio de sesión, su cuenta será "
    "bloqueada temporalmente por 15 minutos. Si necesita acceso inmediato, "
    "contacte al administrador del sistema."
)

# --- 4. Interfaz Principal ---
pdf.add_page()
pdf.chapter_title("4. Interfaz Principal")
pdf.body_text(
    "Tras iniciar sesión, verá la ventana principal con dos áreas principales:"
)
pdf.section_title("4.1 Barra Lateral (Menú)")
pdf.body_text(
    "A la izquierda se encuentra el menú de navegación con los módulos "
    "disponibles según su rol de usuario. Haga clic en cualquier opción "
    "para abrir ese módulo."
)

pdf.section_title("4.2 Área de Trabajo")
pdf.body_text(
    "A la derecha se muestra el contenido del módulo seleccionado. Cada "
    "módulo tiene su propia interfaz con tablas, formularios y botones "
    "de acción."
)

pdf.section_title("4.3 Timeout de Sesión")
pdf.body_text(
    "Por seguridad, la sesión se cierra automáticamente después de 30 "
    "minutos de inactividad. Si su sesión expira, verá un mensaje "
    "informativo y deberá volver a iniciar sesión."
)

# --- 5. Dashboard ---
pdf.chapter_title("5. Módulo Dashboard")
pdf.body_text(
    "El Dashboard es la pantalla principal que se muestra al iniciar sesión. "
    "Aquí encontrará un resumen de indicadores clave del negocio, incluyendo "
    "totales de clientes, llantas en inventario, facturación del día y "
    "alertas importantes."
)

# --- 6. Clientes ---
pdf.add_page()
pdf.chapter_title("6. Módulo Clientes")
pdf.body_text(
    "El módulo de Clientes permite gestionar la base de datos de clientes."
)

pdf.section_title("6.1 Listado de Clientes")
pdf.body_text(
    "Al abrir el módulo, verá una tabla con todos los clientes registrados. "
    "Puede buscar clientes usando el campo de búsqueda por nombre, NIT, "
    "teléfono o email."
)

pdf.section_title("6.2 Crear un Cliente")
pdf.step(1, "Haga clic en '+ Nuevo Cliente'.")
pdf.step(2, "Complete los campos obligatorios (Nombre y NIT).")
pdf.step(3, "Complete los campos opcionales (Teléfono, Celular, Email, Dirección, Ciudad).")
pdf.step(4, "Haga clic en 'Guardar'.")

pdf.section_title("6.3 Editar un Cliente")
pdf.step(1, "Seleccione el cliente en la tabla.")
pdf.step(2, "Haga clic en 'Editar'.")
pdf.step(3, "Modifique los campos necesarios.")
pdf.step(4, "Haga clic en 'Guardar'.")

pdf.section_title("6.4 Eliminar un Cliente")
pdf.step(1, "Seleccione el cliente en la tabla.")
pdf.step(2, "Haga clic en 'Eliminar'.")
pdf.step(3, "Confirme la eliminación en el mensaje de confirmación.")

# --- 7. Llantas ---
pdf.add_page()
pdf.chapter_title("7. Módulo Llantas")
pdf.body_text(
    "El módulo de Llantas gestiona el inventario de llantas, sus "
    "ubicaciones y estados."
)
pdf.section_title("7.1 Registrar una Llanta")
pdf.step(1, "Abra el módulo Llantas.")
pdf.step(2, "Haga clic en 'Nueva Llanta'.")
pdf.step(3, "Complete los datos: marca, modelo, tamaño, número de serie.")
pdf.step(4, "Asigne una ubicación y estado inicial.")
pdf.step(5, "Guarde los cambios.")

pdf.section_title("7.2 Mover una Llanta")
pdf.body_text(
    "Seleccione la llanta y use la opción 'Mover' para cambiar su "
    "ubicación dentro de la planta."
)

# --- 8. Facturación ---
pdf.chapter_title("8. Módulo Facturación")
pdf.body_text(
    "El módulo de Facturación permite crear y gestionar facturas de venta."
)
pdf.section_title("8.1 Crear una Factura")
pdf.step(1, "Seleccione el cliente.")
pdf.step(2, "Agregue los productos/servicios facturados.")
pdf.step(3, "El sistema calcula automáticamente los totales.")
pdf.step(4, "Haga clic en 'Guardar' para emitir la factura.")

# --- 9. Cartera ---
pdf.chapter_title("9. Módulo Cartera")
pdf.body_text(
    "El módulo de Cartera muestra las cuentas por cobrar y permite "
    "registrar pagos."
)
pdf.section_title("9.1 Registrar un Pago")
pdf.step(1, "Seleccione la factura en la tabla de cartera.")
pdf.step(2, "Haga clic en 'Registrar Pago'.")
pdf.step(3, "Ingrese el monto y la fecha del pago.")
pdf.step(4, "Seleccione el método de pago.")
pdf.step(5, "Guarde el pago.")

# --- 10. Inventario ---
pdf.add_page()
pdf.chapter_title("10. Módulo Inventario")
pdf.body_text(
    "El módulo de Inventario controla los productos y sus movimientos "
    "dentro del almacén."
)
pdf.section_title("10.1 Consultar Inventario")
pdf.body_text(
    "Al abrir el módulo, verá una tabla con todos los productos, sus "
    "cantidades y valores. Puede filtrar por nombre o código."
)
pdf.section_title("10.2 Ajustar Inventario")
pdf.body_text(
    "Use la opción 'Ajustar' para corregir cantidades después de un "
    "inventario físico. Cada ajuste queda registrado en el kardex."
)

# --- 11. Backup ---
pdf.add_page()
pdf.chapter_title("11. Módulo Backup")
pdf.body_text(
    "El módulo de Backup le permite gestionar las copias de seguridad "
    "de la base de datos."
)
pdf.section_title("11.1 Crear un Backup Manual")
pdf.step(1, "Abra el módulo Backup.")
pdf.step(2, "En la pestaña 'Backup/Restore', haga clic en 'Crear Backup'.")
pdf.step(3, "Espere a que se complete el proceso.")
pdf.step(4, "Verá la confirmación con la ruta del archivo.")

pdf.section_title("11.2 Restaurar un Backup")
pdf.step(1, "Seleccione un backup de la lista.")
pdf.step(2, "Haga clic en 'Restaurar'.")
pdf.step(3, "Confirme la operación.")
pdf.step(4, "El sistema renombra la BD actual como safety net y restaura.")

pdf.section_title("11.3 Exportar Datos")
pdf.body_text(
    "Use las pestañas 'Exportar' para descargar los datos de cualquier "
    "tabla en formato CSV o Excel. Los archivos se guardan en la carpeta "
    "de backups."
)

# --- 12. Cerrar Sesión ---
pdf.chapter_title("12. Cierre de Sesión")
pdf.body_text(
    "Para cerrar la sesión, simplemente cierre la ventana principal "
    "haciendo clic en la X de la esquina superior derecha. La sesión "
    "se cerrará automáticamente y se registrará el evento de cierre "
    "en la auditoría."
)
pdf.body_text(
    "Nota: Siempre cierre sesión al terminar su turno, especialmente "
    "en equipos compartidos."
)

# --- 13. Solución de Problemas ---
pdf.add_page()
pdf.chapter_title("13. Solución de Problemas")

pdf.section_title("No puedo iniciar sesión")
pdf.bullet("Verifique que el usuario y contraseña son correctos.")
pdf.bullet("Si su cuenta está bloqueada, espere 15 minutos.")
pdf.bullet("Si olvidó su contraseña, contacte al administrador.")

pdf.section_title("La aplicación no responde")
pdf.bullet("Espere unos segundos — puede estar procesando una operación.")
pdf.bullet("Si no responde después de 30 segundos, cierre y reinicie.")
pdf.bullet("Verifique que no haya otro usuario realizando una operación pesada.")

pdf.section_title("Error al crear un backup")
pdf.bullet("Verifique que hay espacio en disco.")
pdf.bullet("Verifique que la base de datos no esté en uso por otro proceso.")
pdf.bullet("Intente nuevamente; si persiste, contacte al administrador.")

pdf.section_title("Los datos no se actualizan")
pdf.bullet("Use el campo de búsqueda o recargue el módulo.")
pdf.bullet("Cierre y vuelva a abrir el módulo desde el menú lateral.")
pdf.section_title("Contacto de Soporte")
pdf.body_text("Para incidencias técnicas, contacte al administrador del sistema.")

# Save
output = ROOT / "USER_MANUAL.pdf"
pdf.output(str(output))
print(f"USER_MANUAL.pdf generated: {output}")
