#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 18:04:25 2021

@author: ep
"""

with open('__auths.txt','r') as f:
    AUTHS = [L.replace('\r','').replace('\n','') for L in f.readlines()]
