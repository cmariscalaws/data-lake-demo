#!/usr/bin/env python3
import aws_cdk as cdk
from option_a.stack import OptionAStack

app = cdk.App()
OptionAStack(app, "OptionAIngestionDemoPy")
app.synth()
