# Mamba Based Pyhton Installation
See the documents (pdf, docx, and md) for a detailed mamba install instructions.
The next section of this readme shows a quick method, but for powershell and cmd inclusion see the docs mentioned.

# Using the Yamls
1. First install using **Py3p12_Clean.yml**<br>
&nbsp;&nbsp;&nbsp;&nbsp;1.1 `mamba env create -c conda-forge --strict-channel-priority -f Pyp12_Clean.yml`<br>
2. After this finishes, to replicate my general python 3.12 install, we will update it later.<br>
&nbsp;&nbsp;&nbsp;&nbsp;2.1 `mamba env update -c conda-forge --strict-channel-priority -n Py3p12 -f Py3p12_20260904_2245.yml`<br>
3. Next we update it with what we need from mamba, not this does not update modules from pip.<br>
&nbsp;&nbsp;&nbsp;&nbsp;3.1 `mamaba update --all -n Py3p12`<br>
4. If you want to check and update pip installed modules do the following:<br>
&nbsp;&nbsp;&nbsp;&nbsp;4.1<br>
```python
mamba activate Py3p12
python -m pip list --outdated
```

&nbsp;&nbsp;&nbsp;&nbsp;4.2 This may be a long list, and it might be easier to do `mamba env export -n Py3p12 --no-builds > Py3p12_environment.yml` and check the pip section.<br>
