Dim objShell
Dim projectDir
Set objShell = CreateObject("WScript.Shell")
projectDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = projectDir
objShell.Run "cmd /c start ""Emotion AI Server"" /D """ & projectDir & """ server-run.cmd", 0, False
Set objShell = Nothing
