# Opens the Excel model in Excel itself, lets Excel calculate every formula, and
# compares the results with the numbers the Python script computed independently.
# Needs Microsoft Excel installed. With -Save, also stores Excel's calculated
# values in the file so previewers that don't calculate formulas still show numbers.
param([switch]$Save)

$root = Split-Path -Parent $PSScriptRoot
$xlsx = Join-Path $root "Incident_Routing_Impact_Model.xlsx"
$expected = Import-Csv (Join-Path $root "data\processed\impact_scenarios.csv")
$outputs = @("incidents_routed_right_per_month", "handoffs_avoided_per_month", "elapsed_hours_saved_per_month",
             "incidents_newly_meeting_sla_per_month", "analyst_hours_saved_per_month", "analyst_cost_saved_per_month",
             "analyst_cost_saved_per_year", "one_off_cost", "payback_days")
$firstOutputRow = 17  # the row holding the first output formula

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$failures = 0
try {
    $wb = $excel.Workbooks.Open($xlsx)
    $excel.CalculateFull()
    $ws = $wb.Worksheets.Item("Model")
    for ($i = 0; $i -lt $outputs.Count; $i++) {
        for ($s = 0; $s -lt 3; $s++) {
            $fromExcel = [double]$ws.Cells.Item($firstOutputRow + $i, 3 + $s).Value2
            $fromPython = [double]$expected[$s].($outputs[$i])
            $tolerance = [Math]::Max(0.06, [Math]::Abs($fromPython) * 0.0005)  # CSV is rounded to 4 places
            if ([Math]::Abs($fromExcel - $fromPython) -gt $tolerance) {
                $failures++
                "FAIL  $($outputs[$i]) [$($expected[$s].scenario)]: Excel $fromExcel vs Python $fromPython"
            }
        }
    }
    if ($Save) { $wb.Save(); "saved Excel's calculated values into the workbook" }
    $wb.Close($false)
}
finally {
    $excel.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
if ($failures -eq 0) { "PASS  all $($outputs.Count * 3) Excel formula results match the Python calculation" } else { "$failures MISMATCH(ES)"; exit 1 }
