#!groovy

    
pipeline {
    agent {
        label 'Operations'
    }
    environment {
        TF_LOG_PATH = "./terraform.log"
        TF_LOG = "DEBUG"
        PATH = "${tool 'Terraform 0.12.31'}:$PATH"
        // VAULT_ADDR="https://vault.ice.dhs.gov"
        // VAULT_ROLE_ID = credentials('vault_role_id')
        // VAULT_SECRET_ID = credentials('vault_secret_id')
    }
    parameters {
        choice(
            choices: ['Build Function', 'Destroy Function'],
            description: 'Choose one',
            name: 'action'
        )
        choice(
            choices: ['ice-cloud-mgmt', 'ice-prod','maa-nonprod','hsi-nonprod','ero-nonprod','ero-prod'],
            description: 'Choose one',
            name: 'account'
        )
    }
    stages {
        stage ('Terraform init') {
            when {
                expression { params.action == 'Build Function'}
            }
            steps {
                echo "Terraform is initializing"        
                terraforminit(params.account)
            }
        }
        stage ('Terraform apply') {
            when {
                expression { params.action == 'Build Function'}
            }
            steps {
                echo "Terraform is creating/updating aws Devolumizer"        
                terraformapply(params.account)
                // sh 'aws s3 cp orphaned_volumes.json s3://ice-skyhook-data/orphaned_volumes.json' 
            }
        }
        stage ('Terraform destroy') {
            when {
                expression { params.action == 'Destroy Function'}
            }
            steps {
                echo "Terraform is destroying aws Devolumizer"        
                terraformdestroy(params.account)
            }
        }
    }
}


// functions

def terraforminit(String account) {
    echo "Terraform init and Plan:" 
 
    dir("infra") {
        withAWS(credentials: "aws-${account}") {
            sh '''       
            terraform --version
            terraform init -backend-config=${account}.conf
            terraform plan -var-file="${account}".tfvars
            '''
        }
    }
}

def terraformapply(String account) {
    echo "Terraform apply:" 
 
    dir("infra") {
        withAWS(credentials: "aws-${account}") {
            sh '''
            terraform --version
            terraform init -backend-config="${account}".conf
            terraform apply -var-file="${account}".tfvars -auto-approve
            '''
        }
    }
}

def terraformdestroy(String account) {
    echo "Terraform destroy:" 
 
    dir("infra") {
        sh '''
        terraform --version
        terraform init -backend-config="${account}".conf
        terraform destroy -var-file="${account}".tfvars -force
        '''
    }
}
