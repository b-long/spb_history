

Install : 
```
git clone https://github.com/Bioconductor/spb_history.git
cd spb_history
pip install --upgrade -r ./PIP-DEPENDENCIES*
```

Crontab for biocadmin on `staging.bioconductor.org` : 
```
@reboot /home/biocadmin/spb_history/run-archiver.sh
@reboot /home/biocadmin/spb_history/run-django.sh
@reboot /home/biocadmin/spb_history/run-track_build_completion.sh
```
