param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'
$inputFile = (Resolve-Path -LiteralPath $Path).ProviderPath

if (-not ('NativeBootStudioCrc32' -as [type])) {
    Add-Type -TypeDefinition @'
public static class NativeBootStudioCrc32
{
    public static uint Compute(byte[] data)
    {
        uint crc = 0xffffffff;
        foreach (byte value in data)
        {
            crc ^= value;
            for (int bit = 0; bit < 8; bit++)
                crc = (crc & 1) != 0 ? (crc >> 1) ^ 0xedb88320 : crc >> 1;
        }
        return crc ^ 0xffffffff;
    }
}
'@
}

([NativeBootStudioCrc32]::Compute([System.IO.File]::ReadAllBytes($inputFile))).ToString('x8')
