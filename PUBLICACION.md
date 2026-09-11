# Publicación de la página protegida

## Arquitectura elegida

Vercel administra el dominio, pero el backend se despliega como contenedor con disco persistente. Vercel Functions no es el destino de SQLite. El código se sincroniza desde GitHub y el subdominio público apunta al servicio backend mediante DNS.

## Qué incluye

- Pantalla de ingreso con contraseña compartida.
- Sesión firmada de ocho horas mediante cookie `HttpOnly` y `SameSite=Lax`.
- Protección contra falsificación de formularios.
- Bloqueo temporal después de cinco contraseñas incorrectas en quince minutos.
- Acceso protegido a cargas, historial, informes y ejecución del LLM.
- Límites de archivos existentes y cabeceras de seguridad.
- Contenedor reproducible y almacenamiento persistente para SQLite, salidas y corridas.

## Variables obligatorias

- `AGENT_PASSWORD`: contraseña de al menos 12 caracteres.
- `SESSION_SECRET`: valor aleatorio de al menos 32 caracteres, diferente de la contraseña.
- `OPENAI_API_KEY`: necesaria para completar la interpretación del LLM.
- `PUBLIC_BASE_URL`: URL pública iniciada con `https://`, para activar cookies seguras.
- `AGENT_DATA_DIR`: directorio persistente; en Docker se usa `/app/runtime`.

No guardar valores reales en `.env.example`, el repositorio ni capturas.

## Despliegue

1. Crear un servicio web a partir del `Dockerfile`.
2. Configurar las variables como secretos del proveedor.
3. Montar un volumen persistente en `/app/runtime`.
4. Exponer el puerto 8000 exclusivamente detrás del HTTPS administrado por el proveedor.
5. Configurar el chequeo de salud en `/salud`.
6. Abrir la URL, verificar que solicite contraseña y realizar primero una corrida de prueba no productiva.

No debe publicarse directamente el puerto 8000 en Internet sin un proxy HTTPS. La aplicación está pensada para un equipo reducido. Una contraseña compartida permite acceso, pero no identifica qué empleado realizó cada acción. Si se requiere auditoría individual, el siguiente paso debe ser incorporar usuarios separados o inicio de sesión corporativo.

## Respaldo

El volumen `/app/runtime` contiene la base y las salidas. Debe incluirse en la política de respaldo del proveedor. Antes de publicar corridas o entradas, anonimizar cualquier dato personal u operativo sensible.
