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

' Call the batch file with the concatenated arguments
shell.Run "cmd /c circusd.bat " & cmdArgs, 0, False

Set shell=Nothing
