

Install : 
```
git clone https://github.com/Bioconductor/spb_history.git
cd spb_history
# For now (Nov 2019) you need to use the python3 branch. This is until
# the python3 branch gets merged into the master branch:
git checkout python3
pip3 install --upgrade -r ./PIP-DEPENDENCIES*
```

**Note:** Use `pip` instead of `pip3` on the Windows builder.

Crontab for biocadmin on `staging.bioconductor.org` : 
```
@reboot /home/biocadmin/spb_history/run-archiver.sh
@reboot /home/biocadmin/spb_history/run-django.sh
@reboot /home/biocadmin/spb_history/run-track_build_completion.sh
```
