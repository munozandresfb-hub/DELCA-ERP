"""Generate ADMIN_MANUAL.pdf using fpdf2."""

from fpdf import FPDF
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/arial.ttf"
FONT_BD = "C:/Windows/Fonts/arialbd.ttf"
FONT_I = "C:/Windows/Fonts/ariali.ttf"


class AdminManual(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("ArialUni", "", FONT, uni=True)
        self.add_font("ArialUni", "B", FONT_BD, uni=True)
        self.add_font("ArialUni", "I", FONT_I, uni=True)

    def header(self):
        if self.page_no() > 1:
            self.set_font("ArialUni", "I", 8)
            self.cell(0, 5, "DELCA ERP - Manual de Administracion", align="C")
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


pdf = AdminManual()
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
pdf.cell(0, 12, "Manual de Administración", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_font("ArialUni", "", 11)
pdf.set_text_color(127, 140, 141)
pdf.cell(0, 8, "Versión 1.0.0 - Junio 2026", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "Guía Técnica para Administradores del Sistema", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.cell(0, 8, "DELCA", align="C", new_x="LMARGIN", new_y="NEXT")

# --- TOC ---
pdf.add_page()
pdf.chapter_title("Índice")
toc = [
    "1. Introducción",
    "2. Instalación y Despliegue",
    "3. Configuración del Sistema (.env)",
    "4. Administración de Usuarios",
    "5. Roles y Permisos (RBAC)",
    "6. Backup y Recuperación",
    "7. Monitoreo y Logs",
    "8. Auditoría",
    "9. Seguridad",
    "10. Base de Datos",
    "11. Solución de Problemas Técnicos",
    "12. Mantenimiento Preventivo",
]
for item in toc:
    pdf.body_text(item)

# --- 1. Introducción ---
pdf.add_page()
pdf.chapter_title("1. Introducción")
pdf.body_text(
    "Este manual está dirigido al administrador del sistema DELCA ERP. "
    "Cubre instalación, configuración, administración de usuarios, "
    "gestión de backups, monitoreo y resolución de problemas técnicos."
)

# --- 2. Instalación ---
pdf.chapter_title("2. Instalación y Despliegue")
pdf.section_title("2.1 Instalación desde el Instalador")
pdf.step(1, "Ejecute DELCA_ERP_Setup_1.0.0.exe como Administrador.")
pdf.step(2, "Siga el asistente de instalación (siguiente, siguiente...).")
pdf.step(3, "Seleccione si desea crear acceso directo en el escritorio.")
pdf.step(4, "El instalador crea las carpetas: data/, backups/, logs/.")
pdf.step(5, "Al finalizar, puede iniciar la aplicación inmediatamente.")

pdf.section_title("2.2 Compilación desde Código Fuente")
pdf.body_text("Ver BUILD.md para instrucciones detalladas.")
pdf.bullet("Requisito: Python 3.13+ con venv configurado.")
pdf.bullet("PyInstaller para compilar el EXE.")
pdf.bullet("Inno Setup 6+ para generar el instalador.")

pdf.section_title("2.3 Estructura de Directorios tras Instalación")
pdf.body_text(
    "C:\\Program Files\\DELCA ERP\\\n"
    "  ├── DELCA_ERP.exe          # Ejecutable principal\n"
    "  ├── .env                    # Configuración del sistema\n"  
    "  ├── data/                   # Base de datos SQLite\n"
    "  ├── backups/                # Backups automáticos\n"
    "  ├── logs/                   # Logs del sistema\n"
    "  └── docs/                   # Documentación técnica"
)

# --- 3. Configuración .env ---
pdf.add_page()
pdf.chapter_title("3. Configuración del Sistema (.env)")
pdf.body_text(
    "El archivo .env centraliza toda la configuración del sistema. "
    "Se encuentra en la raíz de la instalación. Si no existe, el "
    "instalador lo crea automáticamente."
)

pdf.section_title("3.1 Variables Disponibles")
pdf.set_font("Courier", "", 9)
pdf.multi_cell(0, 4,
    "# Database\n"
    "DATABASE_URL=sqlite:///C:/ProgramData/DELCA/delca.db\n"
    "DB_ECHO=false\n\n"
    "# Paths\n"
    "LOG_DIR=C:/ProgramData/DELCA/logs\n"
    "BACKUP_DIR=C:/ProgramData/DELCA/backups\n"
    "DATA_DIR=C:/ProgramData/DELCA/data\n\n"
    "# Security\n"
    "SECRET_KEY=change-me-in-production"
)
pdf.ln(4)
pdf.set_font("ArialUni", "", 10)

pdf.section_title("3.2 Migrar a PostgreSQL (Futuro)")
pdf.body_text(
    "Para usar PostgreSQL, cambie DATABASE_URL a:\n"
    "DATABASE_URL=postgresql://usuario:password@localhost:5432/delca"
)

pdf.section_title("3.3 Cambiar Ubicación de la BD")
pdf.body_text(
    "Para usar una ubicación diferente para la base de datos, "
    "modifique DATABASE_URL en .env. El sistema creará la BD "
    "en la nueva ubicación automáticamente."
)

# --- 4. Usuarios ---
pdf.add_page()
pdf.chapter_title("4. Administración de Usuarios")
pdf.body_text(
    "La gestión de usuarios se realiza desde el módulo 'Usuarios' "
    "en la barra lateral, visible solo para usuarios con rol ADMIN."
)

pdf.section_title("4.1 Crear un Usuario")
pdf.step(1, "Abra el módulo Usuarios.")
pdf.step(2, "Haga clic en '+ Nuevo Usuario'.")
pdf.step(3, "Ingrese nombre completo, username y contraseña.")
pdf.step(4, "Seleccione el rol (ADMIN, GERENCIA, OPERADOR, CONSULTA).")
pdf.step(5, "Haga clic en 'Guardar'.")
pdf.body_text(
    "El usuario creado deberá cambiar su contraseña en el primer inicio de sesión."
)

pdf.section_title("4.2 Editar un Usuario")
pdf.step(1, "Seleccione el usuario en la tabla.")
pdf.step(2, "Haga clic en 'Editar'.")
pdf.step(3, "Puede modificar nombre y rol. El username no se puede cambiar.")
pdf.step(4, "Guarde los cambios.")

pdf.section_title("4.3 Resetear Contraseña")
pdf.step(1, "Seleccione el usuario.")
pdf.step(2, "Haga clic en 'Reset Password'.")
pdf.step(3, "Ingrese la nueva contraseña (debe cumplir la política de seguridad).")
pdf.step(4, "El usuario deberá cambiarla al iniciar sesión.")

pdf.section_title("4.4 Desactivar un Usuario")
pdf.step(1, "Seleccione el usuario.")
pdf.step(2, "Haga clic en 'Desactivar'.")
pdf.step(3, "Confirme la desactivación.")
pdf.body_text(
    "El usuario desactivado no podrá iniciar sesión. No se puede "
    "desactivar el propio usuario administrador."
)

# --- 5. Roles y Permisos ---
pdf.add_page()
pdf.chapter_title("5. Roles y Permisos (RBAC)")
pdf.body_text(
    "El sistema utiliza Control de Acceso Basado en Roles (RBAC) "
    "con 4 roles predefinidos y 26 permisos granulares."
)

pdf.section_title("5.1 Roles del Sistema")
roles_info = [
    ("ADMIN", "Acceso total a todos los módulos y funciones, incluyendo "
     "gestión de usuarios y configuración del sistema."),
    ("GERENCIA", "Acceso operativo completo a todos los módulos de negocio. "
     "No puede gestionar usuarios ni eliminar registros."),
    ("OPERADOR", "Acceso a operaciones diarias: crear, editar y consultar. "
     "No puede anular facturas, eliminar clientes/llantas, ni gestionar usuarios."),
    ("CONSULTA", "Acceso solo de lectura a todos los módulos. "
     "No puede crear, editar ni eliminar ningún registro."),
]
for name, desc in roles_info:
    pdf.set_font("ArialUni", "B", 10)
    pdf.cell(0, 6, name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ArialUni", "", 10)
    pdf.multi_cell(0, 5, desc)
    pdf.ln(3)

pdf.section_title("5.2 Estructura de Permisos")
pdf.body_text(
    "Cada permiso sigue el formato '{modulo}.{accion}'. Por ejemplo:\n"
    "- clientes.ver: Ver listado de clientes\n"
    "- clientes.crear: Crear nuevos clientes\n"
    "- clientes.editar: Editar clientes existentes\n"
    "- clientes.eliminar: Eliminar clientes"
)
pdf.body_text(
    "Los permisos se asignan a roles en bootstrap_rbac.py. "
    "Para modificar los permisos de un rol, edite ROLE_PERMISSIONS "
    "en ese archivo y reinicie la aplicación."
)

# --- 6. Backup ---
pdf.add_page()
pdf.chapter_title("6. Backup y Recuperación")
pdf.body_text(
    "El sistema incluye un módulo completo de backup con las siguientes "
    "capacidades:"
)
pdf.bullet("Backup manual con un clic desde la UI.")
pdf.bullet("WAL checkpoint (TRUNCATE) antes de cada copia.")
pdf.bullet("Restauraci\u00f3n segura: renombra la BD actual a .bak antes de restore.")
pdf.bullet("Exportaci\u00f3n de datos a CSV y Excel (todas las tablas).")
pdf.bullet("Verificaci\u00f3n de integridad (PRAGMA integrity_check).")
pdf.bullet("Retenci\u00f3n autom\u00e1tica de 30 backups.")

pdf.section_title("6.1 Política de Retención")
pdf.body_text(
    "El sistema mantiene un m\u00e1ximo de 30 archivos de backup. "
    "Cuando se supera este l\u00edmite, se elimina el backup m\u00e1s antiguo "
    "autom\u00e1ticamente."
)

pdf.section_title("6.2 Procedimiento de Recuperación de Desastres")
pdf.step(1, "Si la BD activa est\u00e1 corrupta, intente restaurar desde un backup en la UI.")
pdf.step(2, "Si la UI no est\u00e1 disponible, localice el backup m\u00e1s reciente en backups/.")
pdf.step(3, "Detenga la aplicaci\u00f3n.")
pdf.step(4, "Renombre 'data/delca.db' a 'data/delca.db.corrupto'.")
pdf.step(5, "Copie el backup a 'data/delca.db'.")
pdf.step(6, "Reinicie la aplicaci\u00f3n.")
pdf.step(7, "Verifique la integridad desde el m\u00f3dulo Backup.")

# --- 7. Monitoreo ---
pdf.add_page()
pdf.chapter_title("7. Monitoreo y Logs")
pdf.section_title("7.1 Archivos de Log")
pdf.body_text(
    "El sistema escribe logs rotativos en logs/delca.log con:"
)
pdf.bullet("Tama\u00f1o m\u00e1ximo: 5 MB por archivo.")
pdf.bullet("Retenci\u00f3n: 3 archivos rotativos.")
pdf.bullet("Formato: timestamp - logger - nivel - mensaje.")
pdf.bullet("Nivel: WARNING (oculta DEBUG/INFO de SQLAlchemy).")

pdf.section_title("7.2 Indicadores a Monitorear")
pdf.bullet("Errores de conexi\u00f3n a BD.")
pdf.bullet("Fallos de autenticaci\u00f3n repetidos (posible ataque).")
pdf.bullet("Tiempos de backup elevados.")
pdf.bullet("Errores de exportaci\u00f3n de datos.")

# --- 8. Auditoría ---
pdf.chapter_title("8. Auditoría")
pdf.body_text(
    "Todas las acciones sensibles quedan registradas en la tabla "
    "'auditoria' de la base de datos, incluyendo:"
)
pdf.bullet("Inicios de sesi\u00f3n exitosos (LOGIN).")
pdf.bullet("Intentos fallidos de inicio de sesi\u00f3n (FALLO_LOGIN).")
pdf.bullet("Cierres de sesi\u00f3n (LOGOUT).")
pdf.bullet("Cambios de contrase\u00f1a (CAMBIO_PASSWORD).")
pdf.bullet("Operaciones CRUD en usuarios (CREATE, UPDATE, DELETE).")
pdf.body_text(
    "Para consultar la auditor\u00eda, acceda directamente a la base de datos "
    "o espere una futura interfaz de visualizaci\u00f3n."
)

# --- 9. Seguridad ---
pdf.add_page()
pdf.chapter_title("9. Seguridad")
pdf.section_title("9.1 Política de Contraseñas")
pdf.bullet("Longitud m\u00ednima: 8 caracteres.")
pdf.bullet("Debe contener: may\u00fascula, min\u00fascula, d\u00edgito, car\u00e1cter especial.")
pdf.bullet("Expiraci\u00f3n: 90 d\u00edas.")
pdf.bullet("Cambio forzado en primer inicio de sesi\u00f3n.")

pdf.section_title("9.2 Bloqueo de Cuenta")
pdf.bullet("5 intentos fallidos consecutivos.")
pdf.bullet("Bloqueo temporal de 15 minutos.")
pdf.bullet("El administrador puede resetear el contador desde 'Reset Password'.")

pdf.section_title("9.3 Sesiones")
pdf.bullet("Timeout de inactividad: 30 minutos.")
pdf.bullet("Sesi\u00f3n \u00fanica por usuario (singleton).")

pdf.section_title("9.4 Recomendaciones de Seguridad")
pdf.bullet("Cambiar la contrase\u00f1a del usuario admin inmediatamente.")
pdf.bullet("No compartir credenciales entre usuarios.")
pdf.bullet("Configurar SECRET_KEY en .env con un valor \u00fanico.")
pdf.bullet("Realizar backups peri\u00f3dicos (diario recomendado).")
pdf.bullet("Revisar logs de auditor\u00eda peri\u00f3dicamente.")

# --- 10. Base de Datos ---
pdf.add_page()
pdf.chapter_title("10. Base de Datos")
pdf.section_title("10.1 Esquema")
pdf.body_text(
    "El sistema utiliza SQLite en WAL mode con 13 tablas. "
    "El esquema completo est\u00e1 documentado en Database_er.md."
)

pdf.section_title("10.2 Respaldo de BD")
pdf.body_text(
    "La BD se encuentra en data/delca.db (o la ruta configurada en .env). "
    "Siempre use el m\u00f3dulo Backup para hacer copias de seguridad. "
    "No copie la BD manualmente mientras la aplicaci\u00f3n est\u00e9 en ejecuci\u00f3n."
)

pdf.section_title("10.3 Mantenimiento de BD")
pdf.bullet("Ejecutar PRAGMA integrity_check semanalmente.")
pdf.bullet("Monitorear el tama\u00f1o de la BD (crece con el uso).")
pdf.bullet("Para BD muy grandes (>1 GB), considerar migrar a PostgreSQL.")

# --- 11. Solución de Problemas ---
pdf.add_page()
pdf.chapter_title("11. Soluci\u00f3n de Problemas T\u00e9cnicos")

problems = [
    ("La aplicaci\u00f3n no inicia",
     "Verifique que el .env existe y DATABASE_URL es correcta.\n"
     "Revise logs/delca.log para errores.\n"
     "Verifique que el archivo de BD no est\u00e9 corrupto."),
    ("Error 'database is locked'",
     "Cierre todas las instancias de la aplicaci\u00f3n.\n"
     "Elimine el archivo 'delca.db.wal' y 'delca.db.shm' si existen.\n"
     "Reinicie la aplicaci\u00f3n."),
    ("Error al crear backup",
     "Verifique que hay espacio en disco.\n"
     "Verifique permisos de escritura en backups/.\n"
     "Verifique que la BD no est\u00e9 corrupta (PRAGMA integrity_check)."),
    ("Error al restaurar backup",
     "Verifique que el archivo de backup es un SQLite v\u00e1lido.\n"
     "Si la restauraci\u00f3n falla, el safety net .bak preserva la BD original."),
    ("Usuario bloqueado",
     "Esperar 15 minutos (desbloqueo autom\u00e1tico).\n"
     "O usar 'Reset Password' desde administraci\u00f3n para resetear intentos."),
    ("La UI no responde",
     "Esperar 30 segundos (puede estar procesando).\n"
     "Revisar logs/delca.log por errores de SQLAlchemy.\n"
     "Si persiste, cerrar y reiniciar."),
]
for title, solution in problems:
    pdf.set_font("ArialUni", "B", 10)
    pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("ArialUni", "", 10)
    pdf.multi_cell(0, 5, solution)
    pdf.ln(4)

# --- 12. Mantenimiento ---
pdf.add_page()
pdf.chapter_title("12. Mantenimiento Preventivo")
pdf.body_text("Calendario recomendado de tareas de administraci\u00f3n:")

tasks = [
    ("Diario", "Verificar que el backup autom\u00e1tico se haya completado."),
    ("Diario", "Revisar logs/delca.log por errores cr\u00edticos."),
    ("Semanal", "Ejecutar PRAGMA integrity_check desde m\u00f3dulo Backup."),
    ("Semanal", "Revisar tabla auditor\u00eda por eventos sospechosos."),
    ("Mensual", "Revisar y ajustar permisos de usuarios."),
    ("Mensual", "Verificar tama\u00f1o de la BD."),
    ("Trimestral", "Recordar a usuarios cambiar contrase\u00f1as (expiran a los 90 d\u00edas)."),
    ("Trimestral", "Realizar prueba de restauraci\u00f3n de backup."),
]
for freq, task in tasks:
    pdf.set_font("ArialUni", "B", 10)
    pdf.cell(20, 6, freq + ":")
    pdf.set_font("ArialUni", "", 10)
    pdf.multi_cell(0, 6, task)
    pdf.ln(2)

# Save
output = ROOT / "ADMIN_MANUAL.pdf"
pdf.output(str(output))
print(f"ADMIN_MANUAL.pdf generated: {output}")
