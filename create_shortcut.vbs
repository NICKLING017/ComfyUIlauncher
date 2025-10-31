Dim oWS
Set oWS = CreateObject("WScript.Shell")

Dim sLinkFile
Dim sTarget
Dim sWorkDir
Dim sIcon

If WScript.Arguments.Count < 3 Then
  WScript.Echo "Usage: create_shortcut.vbs <lnk> <target> <workdir> [icon]"
  WScript.Quit 1
End If

sLinkFile = WScript.Arguments(0)
sTarget   = WScript.Arguments(1)
sWorkDir  = WScript.Arguments(2)

If WScript.Arguments.Count >= 4 Then
  sIcon = WScript.Arguments(3)
Else
  sIcon = ""
End If

Dim oLink
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = sTarget
oLink.WorkingDirectory = sWorkDir
If sIcon <> "" Then
  oLink.IconLocation = sIcon
End If
oLink.WindowStyle = 1
oLink.Save