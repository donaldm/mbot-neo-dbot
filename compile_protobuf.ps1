$scriptPath = split-path -parent $MyInvocation.MyCommand.Definition
protoc -I=protobufs --python_out=messages protobufs\DBotCommand.proto