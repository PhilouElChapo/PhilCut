param([string]$Dossier = "")
# Cherche les bibliothèques (DLL) dont les moteurs d'IA de PhilCut ont besoin et qui manquent sur ce poste.
if (-not $Dossier) {
    $cands = @("$env:APPDATA\PhilCut\ia\moteurs") + (Get-ChildItem -Path "$env:USERPROFILE" -Recurse -Depth 4 -Directory -Filter moteurs -ErrorAction SilentlyContinue |
              Where-Object { $_.FullName -like "*\donnees\ia\moteurs" } | ForEach-Object { $_.FullName })
    $Dossier = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Dossier -or -not (Test-Path $Dossier)) { Write-Host "Dossier des moteurs introuvable : donnez-le avec -Dossier" -ForegroundColor Red; return }
Write-Host "Moteurs : $Dossier"

function Get-Imports([string]$f) {
    $b = [IO.File]::ReadAllBytes($f)
    if ($b.Length -lt 64 -or $b[0] -ne 0x4D -or $b[1] -ne 0x5A) { return @() }
    $pe = [BitConverter]::ToInt32($b, 0x3C)
    $nsec = [BitConverter]::ToUInt16($b, $pe + 6)
    $optSize = [BitConverter]::ToUInt16($b, $pe + 20)
    $opt = $pe + 24
    $magic = [BitConverter]::ToUInt16($b, $opt)
    $dd = if ($magic -eq 0x20B) { $opt + 112 } else { $opt + 96 }
    $secs = $opt + $optSize
    function RvaOff([uint32]$rva) {
        for ($i = 0; $i -lt $nsec; $i++) {
            $s = $secs + 40 * $i
            $va = [BitConverter]::ToUInt32($b, $s + 12)
            $taille = [Math]::Max([BitConverter]::ToUInt32($b, $s + 8), [BitConverter]::ToUInt32($b, $s + 16))
            if ($rva -ge $va -and $rva -lt $va + $taille) { return $rva - $va + [BitConverter]::ToUInt32($b, $s + 20) }
        }
        return -1
    }
    $noms = @()
    foreach ($entree in @(@(1, 20, 12), @(13, 32, 4))) {        # imports normaux, puis imports différés
        $rva = [BitConverter]::ToUInt32($b, $dd + 8 * $entree[0])
        if ($rva -eq 0) { continue }
        $o = RvaOff $rva
        while ($o -gt 0 -and $o + $entree[1] -le $b.Length) {
            $n = [BitConverter]::ToUInt32($b, $o + $entree[2])
            if ($n -eq 0) { break }
            $p = RvaOff $n
            if ($p -lt 0) { break }
            $e = $p; while ($b[$e] -ne 0) { $e++ }
            $noms += [Text.Encoding]::ASCII.GetString($b, $p, $e - $p)
            $o += $entree[1]
        }
    }
    return $noms | Sort-Object -Unique
}

$chemins = @("$env:WINDIR\System32") + ($env:PATH -split ';' | Where-Object { $_ })
$rien = $true
foreach ($moteur in Get-ChildItem -Path $Dossier -Directory) {
    $locaux = @{}
    Get-ChildItem -Path $moteur.FullName -Recurse -File -Include *.dll, *.exe | ForEach-Object { $locaux[$_.Name.ToLower()] = $true }
    $manque = @{}
    foreach ($f in Get-ChildItem -Path $moteur.FullName -Recurse -File -Include *.dll, *.exe) {
        foreach ($d in Get-Imports $f.FullName) {
            $dl = $d.ToLower()
            if ($dl -like "api-ms-*" -or $dl -like "ext-ms-*" -or $locaux.ContainsKey($dl)) { continue }
            $trouve = $false
            foreach ($c in $chemins) { if (Test-Path (Join-Path $c $d)) { $trouve = $true; break } }
            if (-not $trouve) { if (-not $manque.ContainsKey($d)) { $manque[$d] = @() }; $manque[$d] += $f.Name }
        }
    }
    if ($manque.Count) {
        $rien = $false
        Write-Host ""
        Write-Host "Moteur $($moteur.Name) : il manque" -ForegroundColor Yellow
        foreach ($k in $manque.Keys) { Write-Host ("  {0}   (demande par {1})" -f $k, (($manque[$k] | Sort-Object -Unique) -join ', ')) }
    } else {
        Write-Host "Moteur $($moteur.Name) : rien ne manque" -ForegroundColor Green
    }
}
if (-not $rien) {
    Write-Host ""
    Write-Host "vcruntime140*.dll, msvcp140*.dll, concrt140.dll : installer Visual C++ 2015-2022 x64 (https://aka.ms/vs/17/release/vc_redist.x64.exe)"
    Write-Host "nvcuda.dll, nvml.dll : pilote Nvidia ; cudart64_*.dll, cublas64_*.dll : fichiers du moteur (le reinstaller)"
    Write-Host "vulkan-1.dll : pilote graphique ; vcomp140.dll : Visual C++"
}
