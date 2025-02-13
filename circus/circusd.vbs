Dim shell, args
Set shell = CreateObject("WScript.Shell")

' Get the arguments passed to the VBScript
Set args = WScript.Arguments
Dim cmdArgs
cmdArgs = ""

' Concatenate the arguments into a single string
For i = 0 To args.Count -1
	cmdArgs = cmdArgs & args(i) & " "
Next

WScript.Echo cmdArgs

' Get the path of the current script
scriptPath = WScript.ScriptFullName

' Extract the directory path
batPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(scriptPath) & "\circusd.bat"

' Call the batch file with the concatenated arguments
shell.Run "cmd /c " & batPath & " " & cmdArgs, 0, False

Set shell=Nothing
