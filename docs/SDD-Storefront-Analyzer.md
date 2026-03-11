# Software Design Document (SDD)
## Storefront Analyzer - Análisis de Escaparates con IA

**Versión:** 1.0
**Fecha:** 2026-01-29
**Fuente:** Figma `prueba-concepto-IA` (LkRNZggizXgbjt0J9NNqRn)

---

## 1. Resumen Ejecutivo

Sistema móvil para validación de escaparates comerciales mediante análisis de imágenes con IA. El usuario captura una foto del escaparate y el sistema la compara contra las guidelines del cliente, devolviendo feedback sobre cumplimiento de KPIs.

### 1.1 Flujo Principal
1. **Portada estática** → Usuario ve detalles de la tarea
2. **Slide-to-action** → Desliza botón para abrir drawer
3. **Drawer de captura** → Selecciona cliente y sube foto
4. **Análisis con IA** → Animaciones mientras procesa
5. **Resultados** → Muestra VÁLIDO/NO VÁLIDO + KPIs con acciones

---

## 2. Arquitectura del Sistema

### 2.1 Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | HTML5, CSS3 (vanilla), JavaScript ES6+ |
| Backend | Python 3.x + FastAPI |
| IA | Claude API (Anthropic) - modelo claude-3-5-haiku |
| Almacenamiento | Sistema de archivos (guidelines PDF por cliente) |

### 2.2 Diagrama de Arquitectura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Mobile App    │────▶│   FastAPI       │────▶│   Claude API    │
│   (HTML/JS)     │◀────│   Backend       │◀────│   (Haiku)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Guidelines     │
                        │  (PDF/cliente)  │
                        └─────────────────┘
```

---

## 3. Especificaciones Frontend

### 3.1 Pantalla 1: Portada (Estática)

**Comentario Figma:** *"En esta pantalla la hacemos estática con los textos que hay aquí"*

#### Elementos UI
| Componente | Descripción | Estilo |
|------------|-------------|--------|
| Status Bar | Simulación iOS (9:41, iconos) | Negro sobre blanco |
| Header | X (cerrar), tags estado/hora/prioridad | `height: 56px` |
| Tags | IN PROGRESS (naranja), 10:00 (gris), prioridad (naranja) | `border-radius: 4px`, `font-weight: 700` |
| Tiempo estimado | "1h 30 min estimado" | `color: #909090`, `font-size: 14px` |
| Título | "Prepara el escaparate con la decoración para el Black Friday" | `font-size: 32px`, `font-weight: 900`, `color: #282828` |
| Descripción | Texto explicativo de la tarea | `font-size: 16px`, `line-height: 1.25` |
| Tag azul | "Adjunta evidencias para completar la tarea" | `background: #C0F0FC`, `color: #07A7F1` |
| Info campaña | Icono + "Preparativos para el Black Friday" + badge | Fila con icono rosa |
| Supervisor | Avatar + "Marc Jane" + "WAITING FOR SIGNATURE" | |
| Fecha | Icono calendario + "20 Oct 2025 12:00" | |
| Ubicación | Icono pin + "Tienda Goya" + badge verde "000" | |
| Sección Pasos | Checklist con avatares y timestamps | Colapsable |
| Sección Guía | Lista con bullets y texto formateado | Colapsable |

#### CSS Crítico
```css
/* Colores principales */
--color-primary: #FA1859;      /* Rosa corporativo */
--color-text: #282828;         /* Texto principal */
--color-text-secondary: #909090;
--color-warning: #FF9700;      /* Tags naranja */
--color-superb: #07A7F1;       /* Azul info */
--color-success: #4CAF50;      /* Verde válido */
--color-error: #E51818;        /* Rojo no válido */
--color-background: #FFFFFF;
--color-surface: #F5F5F5;
```

### 3.2 Botón Slide-to-Action (COMPLETE TASK)

**Comentario Figma:** *"Este botón lo quiero igual a nivel diseño (fijate el corner radius) y quiero que funcione como un slider, tengo que arrastrar el icono de la flecha hasta la derecha para que salte la acción"*

#### Especificaciones
| Propiedad | Valor |
|-----------|-------|
| Altura | 56px |
| Border radius | 48px (pill shape) |
| Background | #FA1859 |
| Texto | "COMPLETE TASK", blanco, bold, 14px |
| Thumb | Círculo 44px, `background: rgba(255,255,255,0.25)` |
| Icono thumb | Flecha derecha (→) blanca |

#### Comportamiento JavaScript
```javascript
// Pseudocódigo
1. onTouchStart: Capturar posición inicial
2. onTouchMove: Mover thumb, fade del texto proporcional
3. onTouchEnd:
   - Si progreso > 75%: Completar slide, abrir drawer
   - Si no: Reset con animación
```

#### Animaciones
- Thumb: `transition: left 0.3s ease`
- Texto: `transition: opacity 0.2s`
- Al completar: Background cambia a #E01550

### 3.3 Pantalla 2: Drawer (Bottom Sheet)

**Comentario Figma:** *"Este botón sacará el siguiente drawer de abajo a arriba"*

#### Estructura
| Elemento | Descripción |
|----------|-------------|
| Overlay | Fondo oscuro `rgba(0,0,0,0.5)` |
| Drawer | Panel blanco desde abajo |
| Handle | Barra gris centrada (indicador drag) |
| Título | "Foto del escaparate" |
| Subtítulo | "Sube una foto frontal del escaparate" |

#### CSS Animación Drawer
```css
.drawer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    border-radius: 24px 24px 0 0;
    transform: translateY(100%);
    transition: transform 0.3s ease-out;
}

.drawer.open {
    transform: translateY(0);
}

.drawer-overlay {
    opacity: 0;
    transition: opacity 0.3s;
}

.drawer-overlay.active {
    opacity: 1;
}
```

### 3.4 Área de Foto (Estados)

#### Estado: Vacío
**Comentario Figma:** *"Hay que añadir el selector de clientes para poder probar el sistema"*

| Elemento | Estilo |
|----------|--------|
| Contenedor | Border dashed 2px #E8E8E8, border-radius 16px |
| Icono cámara | Círculo rosa #FA1859, icono blanco |
| Texto principal | "Foto frontal", gris |
| Texto secundario | "o busca en tu dispositivo", link azul |
| Selector cliente | Dropdown nativo, full-width |
| Botón ANALIZAR | Disabled (gris), sin interacción |
| Botón VOLVER | Secundario, cierra drawer |

#### Estado: Con Foto
| Elemento | Cambio |
|----------|--------|
| Contenedor | Border solid transparent |
| Imagen | `max-height: 320px`, `object-fit: cover`, `border-radius: 14px` |
| Botón ANALIZAR | Activo (#FA1859), con icono sparkle |

### 3.5 Pantalla 3: Analizando

**Comentarios Figma:**
- *"Mientras analiza la imagen tiene que tener un efecto y el icono de abajo también"*
- *"Quiero que mientras analiza, el efecto de la imagen haga la animación como los típicos skeletons que aumentan y disminuyen su color o brillo de forma como latiendo"*
- *"El icono en lugar de rotar tiene que 'latir' como el corazón y que de alguna forma salgan brillos"*
- *"Los textos de abajo se deberían escribir como si fuera un chatbot... simulando que se teclea"*

#### Animaciones Requeridas

**1. Filtro Imagen (Pulsante)**
```css
#photoPreview.analyzing-filter {
    filter: brightness(0.7) saturate(1.5) hue-rotate(190deg);
    animation: image-pulse 2s ease-in-out infinite;
}

@keyframes image-pulse {
    0%, 100% { filter: brightness(0.6) saturate(1.5) hue-rotate(190deg); }
    50% { filter: brightness(0.9) saturate(1.8) hue-rotate(190deg); }
}
```

**2. Borde Azul**
```css
.photo-area.analyzing {
    border-color: #2196F3;
    border-style: solid;
}
```

**3. Icono Sparkle (Latido + Partículas)**
```css
.sparkle-svg.beating {
    animation: sparkle-heartbeat 1.2s ease-in-out infinite;
}

@keyframes sparkle-heartbeat {
    0%, 100% { transform: scale(1); }
    15% { transform: scale(1.3); }
    30% { transform: scale(1); }
    45% { transform: scale(1.15); }
    60% { transform: scale(1); }
}

/* Partículas de brillo */
.sparkle-container.emitting .sparkle-particle {
    animation: sparkle-burst 1.8s ease-out infinite;
}

@keyframes sparkle-burst {
    0% { opacity: 1; transform: translate(0, 0) scale(1); }
    100% { opacity: 0; transform: translate(var(--tx), var(--ty)) scale(0); }
}
```

**4. Texto Typewriter**
```javascript
// Efecto máquina de escribir
function typeMessage(text, element, callback) {
    let i = 0;
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, 40 + Math.random() * 30);
        } else {
            callback?.();
        }
    }
    type();
}

// Mensajes rotativos
const thinkingMessages = [
    "Analizando iluminación",
    "Verificando productos",
    "Comprobando precios",
    "Evaluando disposición"
];
```

**5. Cursor Parpadeante**
```css
.analyzing-cursor {
    animation: cursor-blink 0.7s step-end infinite;
    color: #FA1859;
}

@keyframes cursor-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}
```

### 3.6 Pantalla 4: Resultados

**Comentarios Figma:**
- *"Feedback por cada error que se vea con ese formato"*
- *"Al terminar de procesar, la imagen se hará pequeña con una animación. Si se pulsa volverá a su tamaño original"*
- *"Añadimos el titulo de esta parte como acciones recomendadas a realizar"*

#### Imagen Minimizada
```css
#photoPreview.minimized {
    max-height: 120px;
}

.photo-area.minimized {
    min-height: auto;
}

/* Tap para expandir/colapsar */
#photoPreview {
    cursor: pointer;
    transition: max-height 0.4s ease;
}
```

#### Banner Veredicto
| Estado | Background | Label | Color Label |
|--------|------------|-------|-------------|
| NO VÁLIDO | #FDE8EC | #E51818 (rojo) | Blanco |
| VÁLIDO | #E8F5E9 | #4CAF50 (verde) | Blanco |

```html
<div class="verdict-banner no-valido">
    <span class="verdict-label no-valido">NO VÁLIDO</span>
    <p class="verdict-message">Recomendamos que realices los cambios que te mostramos a continuación.</p>
</div>
```

#### Tarjetas KPI
```html
<div class="kpi-result">
    <svg class="kpi-result-icon"><!-- Sparkle azul --></svg>
    <div class="kpi-result-card">
        <div class="kpi-result-header">
            <span class="kpi-result-category">KPI</span>
            <span class="kpi-result-badge">CRITICAL</span>
        </div>
        <div class="kpi-result-title">Descripción del problema</div>
        <div class="kpi-result-divider"></div>
        <div class="kpi-result-actions-title">Acciones recomendadas a realizar</div>
        <div class="kpi-result-action-label">Acción específica</div>
    </div>
</div>
```

#### Estilos KPI Card
```css
.kpi-result-card {
    background: #F5F5F5;
    border-radius: 12px;
    padding: 16px;
}

.kpi-result-badge {
    background: #FDE8EC;
    color: #E51818;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
}

.kpi-result-icon {
    color: #00A3F5; /* Azul corporativo */
}

.kpi-result-actions-title {
    font-size: 12px;
    font-weight: 700;
    color: #909090;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
```

---

## 4. Especificaciones Backend

### 4.1 Endpoints API

#### POST /analyze
Analiza una imagen de escaparate contra las guidelines del cliente.

**Request:**
```
Content-Type: multipart/form-data

Fields:
- image: File (JPEG/PNG, max 10MB)
- store_id: string (ej: "tienda_goya")
- client_id: string (ej: "cliente_demo")
```

**Response (200 OK):**
```json
{
    "differences": [
        {
            "category": "Iluminación",
            "description": "Zona del escaparate con iluminación insuficiente",
            "action": "Revisar y ajustar los focos del área izquierda",
            "severity": "CRITICAL"
        }
    ],
    "summary": "Se encontraron 2 incumplimientos que requieren atención",
    "valid": false
}
```

**Response (Error):**
```json
{
    "detail": "Error message"
}
```

#### GET /clients
Lista los clientes disponibles para análisis.

**Response:**
```json
{
    "clients": [
        {"id": "cliente_demo", "name": "Cliente Demo"},
        {"id": "retail_corp", "name": "Retail Corp"}
    ]
}
```

#### GET /health
Health check del servicio.

### 4.2 Modelo de Datos

#### Estructura de Directorios
```
guidelines/
├── cliente_demo/
│   ├── guidelines.pdf
│   └── kpis.json
├── retail_corp/
│   ├── guidelines.pdf
│   └── kpis.json
```

#### kpis.json (por cliente)
```json
{
    "client_id": "cliente_demo",
    "client_name": "Cliente Demo",
    "kpis": [
        {
            "id": "iluminacion",
            "name": "Iluminación",
            "description": "Verificar que la iluminación sea uniforme",
            "category": "Iluminación"
        },
        {
            "id": "productos",
            "name": "Productos",
            "description": "Verificar disposición de productos",
            "category": "Visual Merchandising"
        }
    ]
}
```

### 4.3 Integración Claude API

#### Flujo de Análisis
1. Recibir imagen + client_id
2. Cargar guidelines del cliente (PDF → texto)
3. Cargar KPIs configurados
4. Construir prompt con contexto
5. Enviar a Claude API (Haiku)
6. Parsear respuesta estructurada
7. Devolver resultados formateados

#### Prompt Template
```python
ANALYSIS_PROMPT = """
Eres un experto en visual merchandising. Analiza esta imagen de escaparate
según las siguientes guidelines del cliente:

{guidelines_text}

KPIs a evaluar:
{kpis_list}

Para cada incumplimiento encontrado, devuelve:
- category: Categoría del KPI
- description: Descripción breve del problema
- action: Acción recomendada
- severity: CRITICAL | WARNING | INFO

Responde en formato JSON.
"""
```

### 4.4 Configuración

#### Variables de Entorno
```bash
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-haiku-20241022
MAX_IMAGE_SIZE_MB=10
GUIDELINES_PATH=./guidelines
```

#### Config Python
```python
class Settings:
    anthropic_api_key: str
    claude_model: str = "claude-3-5-haiku-20241022"
    max_image_size_mb: int = 10
    guidelines_path: str = "./guidelines"
```

---

## 5. Requisitos No Funcionales

### 5.1 Performance
| Métrica | Objetivo |
|---------|----------|
| Tiempo carga inicial | < 2s |
| Tiempo respuesta análisis | < 10s |
| Animaciones | 60fps |

### 5.2 Compatibilidad
- **Dispositivos:** iOS Safari 15+, Android Chrome 90+
- **Viewport:** 375px - 428px (móvil)
- **Orientación:** Portrait only

### 5.3 UX Móvil
- Touch targets mínimo 44x44px
- Prevenir zoom con `user-scalable=no`
- `touch-action: manipulation` en botones
- Soporte gestos nativos en drawer

---

## 6. Casos de Uso Detallados

### CU-01: Completar Tarea con Análisis

**Actor:** Usuario (empleado tienda)

**Flujo Principal:**
1. Usuario abre la app y ve la portada con detalles de la tarea
2. Usuario desliza el botón "COMPLETE TASK" hacia la derecha
3. Sistema abre el drawer con animación slide-up
4. Usuario selecciona el cliente del dropdown
5. Usuario toca el área de foto o "busca en tu dispositivo"
6. Sistema abre selector de imagen del dispositivo
7. Usuario selecciona/captura foto del escaparate
8. Sistema muestra preview de la imagen
9. Usuario pulsa "ANALIZAR"
10. Sistema muestra animaciones de análisis (imagen pulsante, sparkle latiendo, texto typewriter)
11. Sistema envía imagen a backend → Claude API
12. Sistema recibe respuesta y muestra resultados
13. Imagen se minimiza automáticamente
14. Usuario ve banner VÁLIDO/NO VÁLIDO
15. Usuario revisa tarjetas KPI con acciones recomendadas
16. Usuario puede tocar imagen para expandir/colapsar
17. Usuario pulsa "VOLVER A CARGAR IMAGEN" para nuevo análisis

**Flujos Alternativos:**
- **FA-1:** Error de red → Mostrar mensaje error, restaurar botones
- **FA-2:** Imagen inválida → Mostrar error, permitir reintento
- **FA-3:** Usuario cierra drawer → Reset estado, volver a portada

---

## 7. Checklist de Implementación

### Frontend
- [ ] Portada estática con todos los elementos
- [ ] Botón slide-to-action funcional
- [ ] Drawer con animación slide-up/down
- [ ] Selector de clientes dinámico
- [ ] Área de captura/selección de foto
- [ ] Preview de imagen
- [ ] Animación filtro imagen (pulsante azul)
- [ ] Animación sparkle (latido + partículas)
- [ ] Animación texto typewriter
- [ ] Banner veredicto (VÁLIDO/NO VÁLIDO)
- [ ] Tarjetas KPI con formato correcto
- [ ] Título "Acciones recomendadas a realizar"
- [ ] Imagen minimizada al mostrar resultados
- [ ] Toggle expand/collapse imagen
- [ ] Manejo de errores UI

### Backend
- [ ] Endpoint POST /analyze
- [ ] Endpoint GET /clients
- [ ] Carga de guidelines por cliente
- [ ] Integración Claude API
- [ ] Parseo respuesta estructurada
- [ ] Manejo de errores
- [ ] Validación de imagen
- [ ] Health check endpoint

### Testing
- [ ] Test en iOS Safari
- [ ] Test en Android Chrome
- [ ] Test animaciones 60fps
- [ ] Test respuesta < 10s
- [ ] Test manejo errores

---

## 8. Apéndice: Comentarios Figma Originales

| # | Comentario | Nodo |
|---|------------|------|
| 1 | "En esta pantalla la hacemos estática con los textos que hay aquí" | portada |
| 2 | "Este botón sacará el siguiente drawer de abajo a arriba" | portada |
| 3 | "Hay que añadir el selector de clientes para poder probar el sistema" | drawer |
| 4 | "Esta es una imagen que simula la foto del usuario a su escaparate" | drawer |
| 5 | "Mientras analiza la imagen tiene que tener un efecto y el icono de abajo también por ejemplo que rote el icono de abajo y cambien los textos. Los puntos suspensivos tienen que animarse" | analizando |
| 6 | "Feedback por cada error que se vea con ese formato" | resultados |
| 7 | "Quiero que mientras analiza, el efecto de la imagen haga la animación como los típicos skeletons que aumentan y disminuyen su color o brillo de forma como latiendo" | analizando |
| 8 | "Este botón lo quiero igual a nivel diseño (fijate el corner radius) y quiero que funcione como un slider, tengo que arrastrar el icono de la flecha hasta la derecha para que salte la acción" | portada |
| 9 | "Esto lo quiero que sea del color corporativo que hay en el botón de analizar" | analizando |
| 10 | "Al terminar de procesar, la imagen se hará pequeña con una animación. Si se pulsa volverá a su tamaño original" | resultados |
| 11 | "Añadimos el título de esta parte como acciones recomendadas a realizar y luego debajo ya se escriben las acciones" | resultados |
| - | (Reply) "El icono en lugar de rotar tiene que 'latir' como el corazón y que de alguna forma salgan brillos. Y los textos de abajo se deberían escribir como si fuera un chatbot... simulando que se teclea en el cambio" | analizando |

---

*Documento generado automáticamente a partir del análisis del Figma `prueba-concepto-IA`*
