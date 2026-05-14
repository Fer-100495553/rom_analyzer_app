from __future__ import annotations

import settings_manager

_STRINGS: dict[str, dict[str, str]] = {
    # ── App header ────────────────────────────────────────────────────────
    "app_title": {
        "en": "ROM Analyzer — Vicon Nexus",
        "es": "ROM Analyzer — Vicon Nexus",
    },
    "app_subtitle": {
        "en": "Vicon Nexus  ·  Range of Motion Analysis",
        "es": "Vicon Nexus  ·  Análisis de Rango de Movimiento",
    },
    # ── Settings dialog ───────────────────────────────────────────────────
    "settings_title": {"en": "Settings", "es": "Ajustes"},
    "settings_language_label": {"en": "Language", "es": "Idioma"},
    "settings_theme_label": {"en": "Theme", "es": "Tema"},
    "settings_theme_system": {"en": "System", "es": "Sistema"},
    "settings_theme_dark": {"en": "Dark", "es": "Oscuro"},
    "settings_theme_light": {"en": "Light", "es": "Claro"},
    "settings_close": {"en": "Close", "es": "Cerrar"},
    # ── Screen 1 ──────────────────────────────────────────────────────────
    "s1_card_movements": {
        "en": "SELECT MOVEMENTS TO ANALYZE",
        "es": "SELECCIONAR MOVIMIENTOS A ANALIZAR",
    },
    "s1_not_available": {
        "en": "(not yet available)",
        "es": "(aún no disponible)",
    },
    "s1_select_all": {"en": "Select All", "es": "Seleccionar Todo"},
    "s1_deselect_all": {"en": "Deselect All", "es": "Deseleccionar Todo"},
    "s1_card_laterality": {"en": "LATERALITY", "es": "LATERALIDAD"},
    "s1_bilateral": {"en": "Bilateral", "es": "Bilateral"},
    "s1_bilateral_hint": {
        "en": "one shared C3D per movement → extracts Left + Right",
        "es": "un C3D compartido por movimiento → extrae Izquierda + Derecha",
    },
    "s1_unilateral": {"en": "Unilateral", "es": "Unilateral"},
    "s1_unilateral_hint": {
        "en": "separate C3D per side per movement",
        "es": "C3D separado por lado y movimiento",
    },
    "s1_continue": {
        "en": "Continue to File Import →",
        "es": "Continuar a Importación de Archivos →",
    },
    "s1_err_no_movements_title": {
        "en": "No movements selected",
        "es": "Sin movimientos seleccionados",
    },
    "s1_err_no_movements_msg": {
        "en": "Please select at least one movement before continuing.",
        "es": "Por favor, seleccione al menos un movimiento antes de continuar.",
    },
    # ── Screen 1 — Recording Type ─────────────────────────────────────────
    "s1_card_recording_type": {
        "en": "RECORDING TYPE",
        "es": "TIPO DE GRABACIÓN",
    },
    "s1_rec_continuous": {"en": "Continuous", "es": "Continuo"},
    "s1_rec_continuous_hint": {
        "en": "one C3D per movement, multiple reps → segment manually",
        "es": "un C3D por movimiento, varias reps → segmentar manualmente",
    },
    "s1_rec_individual": {"en": "Individual", "es": "Individual"},
    "s1_rec_individual_hint": {
        "en": "one C3D per repetition → no segmentation needed",
        "es": "un C3D por repetición → sin segmentación",
    },
    "s1_num_reps_label": {
        "en": "Number of repetitions:",
        "es": "Número de repeticiones:",
    },
    # ── Screen 2 ──────────────────────────────────────────────────────────
    "s2_card_import": {
        "en": "IMPORT C3D FILES  (one file per row)",
        "es": "IMPORTAR ARCHIVOS C3D  (un archivo por fila)",
    },
    "s2_hdr_movement": {"en": "Movement", "es": "Movimiento"},
    "s2_hdr_side": {"en": "Side", "es": "Lado"},
    "s2_hdr_file": {"en": "File", "es": "Archivo"},
    "s2_no_file": {"en": "No file selected", "es": "Sin archivo seleccionado"},
    "s2_browse": {"en": "Browse…", "es": "Explorar…"},
    "s2_offset_cb": {
        "en": "Apply offset correction",
        "es": "Aplicar corrección de offset",
    },
    "s2_offset_hint": {
        "en": "Enter the angle value at neutral position (0°)."
             " This value will be subtracted from the entire curve.",
        "es": "Introduzca el valor del ángulo en la posición neutral (0°)."
             " Este valor se restará de toda la curva.",
    },
    "s2_back": {
        "en": "← Back to Configuration",
        "es": "← Volver a Configuración",
    },
    "s2_process": {"en": "Process All →", "es": "Procesar Todo →"},
    "s2_load_error_title": {"en": "Load error", "es": "Error de carga"},
    "s2_load_error_msg": {
        "en": "Could not read C3D file:\n{exc}",
        "es": "No se pudo leer el archivo C3D:\n{exc}",
    },
    "s2_vars_not_found_title": {
        "en": "Variable(s) not found",
        "es": "Variable(s) no encontrada(s)",
    },
    "s2_vars_not_found_msg": {
        "en": "The following expected label(s) were not found in this C3D:\n"
             "  {missing}\n\nAvailable angle outputs:\n  {available}",
        "es": "Las siguientes etiquetas esperadas no se encontraron en este C3D:\n"
             "  {missing}\n\nSalidas de ángulo disponibles:\n  {available}",
    },
    "s2_var_not_found_title": {
        "en": "Variable not found",
        "es": "Variable no encontrada",
    },
    "s2_var_not_found_msg": {
        "en": "Expected label  '{label}'  was not found in this C3D file.\n\n"
             "Available angle outputs:\n  {available}",
        "es": "La etiqueta esperada  '{label}'  no se encontró en este archivo C3D.\n\n"
             "Salidas de ángulo disponibles:\n  {available}",
    },
    "s2_rep_label": {"en": "Rep {n}", "es": "Rep {n}"},
    "s2_card_import_individual": {
        "en": "IMPORT C3D FILES  (one file per repetition)",
        "es": "IMPORTAR ARCHIVOS C3D  (un archivo por repetición)",
    },
    # ── Screen 3 transition ───────────────────────────────────────────────
    "s3_no_results_title": {"en": "No results", "es": "Sin resultados"},
    "s3_no_results_msg": {
        "en": "No movements were successfully segmented."
             " Returning to the import screen.",
        "es": "Ningún movimiento fue segmentado con éxito."
             " Volviendo a la pantalla de importación.",
    },
    # ── Screen 4 ──────────────────────────────────────────────────────────
    "s4_layout_horizontal": {
        "en": "⬌ Horizontal layout",
        "es": "⬌ Diseño horizontal",
    },
    "s4_layout_vertical": {
        "en": "⬍ Vertical layout",
        "es": "⬍ Diseño vertical",
    },
    "s4_card_results": {"en": "RESULTS", "es": "RESULTADOS"},
    "s4_card_overview": {"en": "ROM OVERVIEW", "es": "RESUMEN ROM"},
    "s4_hdr_movement": {"en": "Movement", "es": "Movimiento"},
    "s4_hdr_side": {"en": "Side", "es": "Lado"},
    "s4_hdr_metric": {"en": "Metric", "es": "Métrica"},
    "s4_hdr_n": {"en": "N", "es": "N"},
    "s4_hdr_mean": {"en": "Mean (°)", "es": "Media (°)"},
    "s4_hdr_sd": {"en": "SD (°)", "es": "DT (°)"},
    "s4_hdr_min": {"en": "Min (°)", "es": "Mín (°)"},
    "s4_hdr_max": {"en": "Max (°)", "es": "Máx (°)"},
    "s4_metric_rom": {"en": "ROM", "es": "ROM"},
    "s4_metric_peak": {"en": "Peak", "es": "Máximo"},
    "s4_metric_valley": {"en": "Valley", "es": "Mínimo"},
    "s4_offset_note_prefix": {
        "en": "* Offset correction applied (neutral position calibration): ",
        "es": "* Corrección de offset aplicada (calibración de posición neutral): ",
    },
    "s4_offset_subtracted": {
        "en": "{offset:.1f}° subtracted",
        "es": "{offset:.1f}° restados",
    },
    "s4_export_csv": {"en": "Export CSV", "es": "Exportar CSV"},
    "s4_new_analysis": {"en": "New Analysis →", "es": "Nuevo Análisis →"},
    "s4_generate_report": {"en": "Generate Report", "es": "Generar Informe"},
    "s4_chart_unavailable": {
        "en": "Chart unavailable: {exc}",
        "es": "Gráfico no disponible: {exc}",
    },
    "s4_csv_dialog_title": {"en": "Save CSV", "es": "Guardar CSV"},
    "s4_csv_saved_title": {"en": "Saved", "es": "Guardado"},
    "s4_csv_saved_msg": {
        "en": "CSV saved:\n{path}",
        "es": "CSV guardado:\n{path}",
    },
    "s4_csv_offset_applied": {
        "en": "\n\nOffset correction applied:\n{notes}",
        "es": "\n\nCorrección de offset aplicada:\n{notes}",
    },
    "s4_csv_offset_entry": {
        "en": "  {mv} ({sd}): {off:.1f}° subtracted (neutral position calibration)",
        "es": "  {mv} ({sd}): {off:.1f}° restados (calibración de posición neutral)",
    },
    "s4_report_coming_title": {"en": "Coming soon", "es": "Próximamente"},
    "s4_report_coming_msg": {
        "en": "Report generation will be available in a future version.",
        "es": "La generación de informes estará disponible en una versión futura.",
    },
    "export_chart": {
        "en": "Export Chart",
        "es": "Exportar Gráfico",
    },
    "export_chart_dialog_title": {
        "en": "Save chart as PNG",
        "es": "Guardar gráfico como PNG",
    },
    # ── Individual Review window ──────────────────────────────────────────
    "ir_title": {
        "en": "Review Repetitions — {movement}",
        "es": "Revisar Repeticiones — {movement}",
    },
    "ir_accept": {"en": "Accept & Continue", "es": "Aceptar y Continuar"},
    "ir_exclude": {"en": "Exclude Repetition", "es": "Excluir Repetición"},
    "ir_cancel": {"en": "Cancel", "es": "Cancelar"},
    "ir_hdr_rep":    {"en": "Rep",    "es": "Rep"},
    "ir_hdr_rom":    {"en": "ROM (°)", "es": "ROM (°)"},
    "ir_hdr_peak":   {"en": "Peak (°)", "es": "Máx (°)"},
    "ir_hdr_valley": {"en": "Valley (°)", "es": "Mín (°)"},
    "ir_row_mean":   {"en": "Mean ± SD", "es": "Media ± DT"},
    "ir_excluded_label": {"en": "(excluded)", "es": "(excluida)"},
    "ir_exclude_mode_hint": {
        "en": "Click a row in the table or a curve label to toggle exclusion.",
        "es": "Haz clic en una fila de la tabla o en la etiqueta de curva para excluir.",
    },
    # ── Segmentation window ───────────────────────────────────────────────
    "seg_window_title": {"en": "Segmentation", "es": "Segmentación"},
    "seg_mode_label": {"en": "Mode:", "es": "Modo:"},
    "seg_mode_auto": {"en": "Auto-detect", "es": "Detección automática"},
    "seg_mode_manual": {"en": "Manual", "es": "Manual"},
    "seg_mode_events": {"en": "From Events", "es": "Desde Eventos"},
    "seg_no_segments": {"en": "No segments yet.", "es": "Sin segmentos aún."},
    "seg_accept": {"en": "Accept & Continue", "es": "Aceptar y Continuar"},
    "seg_cancel": {"en": "Cancel", "es": "Cancelar"},
    "seg_reset": {"en": "Reset", "es": "Reiniciar"},
    "seg_prominence": {"en": "Prominence (°):", "es": "Prominencia (°):"},
    "seg_min_distance": {"en": "Min distance (fr):", "es": "Dist. mínima (fr):"},
    "seg_cycle_from": {"en": "Cycle from:", "es": "Ciclo desde:"},
    "seg_valley_valley": {"en": "Valley→Valley", "es": "Valle→Valle"},
    "seg_peak_peak": {"en": "Peak→Peak", "es": "Pico→Pico"},
    "seg_detect": {"en": "Detect", "es": "Detectar"},
    "seg_manual_hint": {
        "en": "Left-click = add marker (alternating start/end)  ·  "
             "Right-click = remove nearest marker",
        "es": "Click izquierdo = añadir marcador (alternando inicio/fin)  ·  "
             "Click derecho = eliminar el más cercano",
    },
    "seg_undo": {"en": "Undo", "es": "Deshacer"},
    "seg_clear": {"en": "Clear", "es": "Limpiar"},
    "seg_markers_placed": {
        "en": "  {n} markers placed → {pairs} complete repetition(s).",
        "es": "  {n} marcadores colocados → {pairs} repetición(es) completa(s).",
    },
    "seg_no_events": {
        "en": "  No events found in this C3D file.",
        "es": "  No se encontraron eventos en este archivo C3D.",
    },
    "seg_start_event": {"en": "Start event:", "es": "Evento de inicio:"},
    "seg_end_event": {"en": "End event:", "es": "Evento de fin:"},
    "seg_map_events": {"en": "Map Events", "es": "Mapear Eventos"},
    "seg_accept_warn_title": {"en": "No segments", "es": "Sin segmentos"},
    "seg_accept_warn_msg": {
        "en": "Please detect or mark at least one repetition before accepting.",
        "es": "Por favor, detecte o marque al menos una repetición antes de aceptar.",
    },
    "seg_no_pairs_title": {"en": "No segments", "es": "Sin segmentos"},
    "seg_no_pairs_msg": {
        "en": "No complete pairs found between '{start}' and '{end}'.",
        "es": "No se encontraron pares completos entre '{start}' y '{end}'.",
    },
    "seg_n_segments": {
        "en": "{n} segment(s)",
        "es": "{n} segmento(s)",
    },
    "seg_detect_error": {"en": "Detection error", "es": "Error de detección"},
    "seg_initial_markers": {
        "en": "  0 markers placed.",
        "es": "  0 marcadores colocados.",
    },
    "seg_halfcycle_direction": {
        "en": "Half-cycle direction",
        "es": "Dirección del semiciclo",
    },
    "seg_half_peak_to_valley": {"en": "Peak to Valley", "es": "Pico a Valle"},
    "seg_half_valley_to_peak": {"en": "Valley to Peak", "es": "Valle a Pico"},
    "seg_reset_selection": {"en": "Reset Selection", "es": "Restablecer Selección"},
    "seg_rep_excluded": {"en": "(excluded)", "es": "(excluida)"},
    "seg_no_active_title": {
        "en": "No active segments",
        "es": "Sin segmentos activos",
    },
    "seg_no_active_msg": {
        "en": "All segments are excluded. Re-include at least one before accepting.",
        "es": "Todos los segmentos están excluidos. Reactive al menos uno antes de aceptar.",
    },
    # ── Excel Export ──────────────────────────────────────────────────────────
    "s4_export_xlsx": {"en": "Export Excel", "es": "Exportar Excel"},
    "s4_xlsx_win_title": {"en": "Export to Excel", "es": "Exportar a Excel"},
    "s4_xlsx_select_sheets": {
        "en": "Select sheets to include:",
        "es": "Seleccionar hojas a incluir:",
    },
    "s4_xlsx_sheet_summary": {"en": "Summary", "es": "Resumen"},
    "s4_xlsx_sheet_rep_detail": {
        "en": "Repetitions Detail",
        "es": "Detalle de Repeticiones",
    },
    "s4_xlsx_sheet_raw_data": {"en": "Raw Data", "es": "Datos Sin Procesar"},
    "s4_xlsx_export_btn": {"en": "Export", "es": "Exportar"},
    "s4_xlsx_no_sheets_title": {
        "en": "No sheets selected",
        "es": "Sin hojas seleccionadas",
    },
    "s4_xlsx_no_sheets_msg": {
        "en": "Please select at least one sheet.",
        "es": "Por favor, seleccione al menos una hoja.",
    },
    "s4_xlsx_saved_title": {"en": "Saved", "es": "Guardado"},
    "s4_xlsx_saved_msg": {
        "en": "Excel saved:\n{path}",
        "es": "Excel guardado:\n{path}",
    },
    "s4_xlsx_dialog_title": {
        "en": "Save Excel file",
        "es": "Guardar archivo Excel",
    },
    # ── Excel export (refactor) ───────────────────────────────────────────────
    "left_side": {
        "en": "LEFT SIDE",
        "es": "LADO IZQUIERDO",
    },
    "right_side": {
        "en": "RIGHT SIDE",
        "es": "LADO DERECHO",
    },
    "frame": {"en": "Frame", "es": "Fotograma"},
    "angle_deg": {"en": "Angle (°)", "es": "Ángulo (°)"},
    "no_data": {"en": "No data", "es": "Sin datos"},
    "rom_summary_chart_title": {
        "en": "ROM Summary",
        "es": "Resumen ROM",
    },
    "s4_excel_dialog_title": {
        "en": "Save Excel Report",
        "es": "Guardar Informe Excel",
    },
    "s4_excel_saved_title": {"en": "Saved", "es": "Guardado"},
    "s4_excel_saved_msg": {
        "en": "Excel report saved:\n{path}",
        "es": "Informe Excel guardado:\n{path}",
    },
    # ── Excel column headers (rep detail + raw data) ──────────────────────────
    "col_time_s": {"en": "Time (s)", "es": "Tiempo (s)"},
    "left_col_peak_frame":   {"en": "Left Peak Frame",    "es": "Fotograma Máx. Izq."},
    "left_col_peak_time":    {"en": "Left Peak Time (s)", "es": "Tiempo Máx. Izq. (s)"},
    "left_col_peak_angle":   {"en": "Left Peak (°)",      "es": "Máximo Izq. (°)"},
    "left_col_valley_frame": {"en": "Left Valley Frame",    "es": "Fotograma Mín. Izq."},
    "left_col_valley_time":  {"en": "Left Valley Time (s)", "es": "Tiempo Mín. Izq. (s)"},
    "left_col_valley_angle": {"en": "Left Valley (°)",      "es": "Mínimo Izq. (°)"},
    "right_col_peak_frame":   {"en": "Right Peak Frame",    "es": "Fotograma Máx. Der."},
    "right_col_peak_time":    {"en": "Right Peak Time (s)", "es": "Tiempo Máx. Der. (s)"},
    "right_col_peak_angle":   {"en": "Right Peak (°)",      "es": "Máximo Der. (°)"},
    "right_col_valley_frame": {"en": "Right Valley Frame",    "es": "Fotograma Mín. Der."},
    "right_col_valley_time":  {"en": "Right Valley Time (s)", "es": "Tiempo Mín. Der. (s)"},
    "right_col_valley_angle": {"en": "Right Valley (°)",      "es": "Mínimo Der. (°)"},
    # ── Distance Comparison export ────────────────────────────────────────────
    "export_distance_comparison": {
        "en": "Distance Comparison",
        "es": "Comparación de Distancia",
    },
    "dist_T8": {"en": "T8", "es": "T8"},
    "dist_C7": {"en": "C7", "es": "C7"},
    "sheet_distance_comparison": {
        "en": "Distance Comparison",
        "es": "Comparación de Distancia",
    },
    "dist_col_metric": {"en": "Metric",  "es": "Métrica"},
    "dist_col_value":  {"en": "Value",   "es": "Valor"},
    "dist_col_units":  {"en": "Units",   "es": "Unidades"},
    "dist_mean":         {"en": "Mean distance",    "es": "Distancia media"},
    "dist_sd":           {"en": "SD",               "es": "DT"},
    "dist_rmse":         {"en": "RMSE",             "es": "RMSE"},
    "dist_max":          {"en": "Max distance",     "es": "Distancia máxima"},
    "dist_p95":          {"en": "95th percentile",  "es": "Percentil 95"},
    "dist_mae_x":        {"en": "MAE X",            "es": "MAE X"},
    "dist_mae_y":        {"en": "MAE Y",            "es": "MAE Y"},
    "dist_mae_z":        {"en": "MAE Z",            "es": "MAE Z"},
    "dist_valid_frames": {"en": "Valid frames",     "es": "Fotogramas válidos"},
    "dist_units_mm":     {"en": "mm",               "es": "mm"},
    "dist_units_none":   {"en": "—",                "es": "—"},
    "dist_y_axis":       {"en": "Distance (mm)",    "es": "Distancia (mm)"},
    # ── Trunk Extended ────────────────────────────────────────────────────────
    "movement_trunk_lateral_inclination": {
        "en": "Trunk Lateral Inclination",
        "es": "Inclinación Lateral del Tronco",
    },
    "plot_flexion_extension": {
        "en": "Flexion / Extension",
        "es": "Flexión / Extensión",
    },
    "plot_lateral_inclination": {
        "en": "Lateral Inclination (primary)",
        "es": "Inclinación Lateral (principal)",
    },
    "plot_axial_rotation": {
        "en": "Axial Rotation",
        "es": "Rotación Axial",
    },
    "err_trunk_markers_missing": {
        "en": "Trunk markers not found in C3D: {missing}",
        "es": "Marcadores de tronco no encontrados en el C3D: {missing}",
    },
}


def t(key: str) -> str:
    """Return the translated string for *key* in the current language."""
    lang = settings_manager.get("language")
    entry = _STRINGS.get(key, {})
    return entry.get(lang, entry.get("en", f"[{key}]"))
