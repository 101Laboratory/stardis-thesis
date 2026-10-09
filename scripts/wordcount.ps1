# Thesis word count - Chinese labels built from Unicode codepoints to avoid encoding issues
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 纯中文字数
$label1 = -join ([char[]]@(0x7EAF, 0x4E2D, 0x6587, 0x5B57, 0x6570))
# 总字数（英文单词 + 中文字）
$label2 = -join ([char[]]@(0x603B, 0x5B57, 0x6570, 0xFF08, 0x82F1, 0x6587, 0x5355, 0x8BCD, 0x20, 0x2B, 0x20, 0x4E2D, 0x6587, 0x5B57, 0xFF09))

$r1 = texcount MainBody.tex -inc -ch-only
$i1 = ($r1 | Select-String 'total' | Select-Object -First 1).LineNumber
Write-Host ("${label1}`t`t`t: " + ($r1[$i1].Trim() -split '\s+')[3])

$r2 = texcount MainBody.tex -inc -chinese
$i2 = ($r2 | Select-String 'total' | Select-Object -First 1).LineNumber
Write-Host ("${label2}`t: " + ($r2[$i2].Trim() -split '\s+')[3])
