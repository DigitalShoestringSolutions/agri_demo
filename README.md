# Power Monitoring Starter Solution

## Install the Shoestring App
In the terminal, run:
- `sudo apt install pipx -y`
- `sudo pipx run shoestring-setup`
- `sudo reboot` if prompted to restart

## Use the Shoestring App to download and configure this Solution
- In the terminal run `shoestring app`, or double click the desktop icon called `Shoestring`.  
- Use the `Download` button and select Power Monitoring. Select the latest release tag.  
- Accept the default install location
- Accept the prompt to Assemble now

## Configure
- Edit each tab to configure each service module. For Power Monitoring, you will need to configure `current-sensing` and optionally `analysis`.

## Build, Start and Stop
If you accepted the prompts to `Build the solution now` and `Start the solution now` at the end of Configuring, the solution will build and start immediately.  
Otherwise use the buttons in `shoestring app`.

# Dashboards
Once the solution is started, open the web browser on the Pi and head to `localhost:3000`. The dashboards available there include:

<img width="1919" height="985" alt="image" src="https://github.com/user-attachments/assets/0c805978-f8e1-429e-bba0-581bd632f4f3" />

<img width="1910" height="782" alt="image" src="https://github.com/user-attachments/assets/846825a4-4553-4807-be6c-0d0aaa7ac3b2" />
