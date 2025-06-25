/**
 * Candidate Form Management JavaScript
 */

class CandidateFormManager {
    constructor() {
        this.form = document.getElementById('candidateForm');
        this.previewElements = {
            initial: document.getElementById('previewInitial'),
            name: document.getElementById('previewName'),
            position: document.getElementById('previewPosition'),
            experience: document.getElementById('previewExperience'),
            salary: document.getElementById('previewSalary')
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeValidation();
        this.updatePreview();
        console.log('Candidate Form Manager initialized');
    }

    bindEvents() {
        // Real-time preview updates
        const nameInput = document.getElementById('name');
        const positionInput = document.getElementById('current_position');
        const experienceInput = document.getElementById('experience_years');
        const salaryInput = document.getElementById('expected_salary');

        nameInput?.addEventListener('input', () => this.updatePreview());
        positionInput?.addEventListener('input', () => this.updatePreview());
        experienceInput?.addEventListener('input', () => this.updatePreview());
        salaryInput?.addEventListener('input', () => this.updatePreview());

        // Form validation
        this.form?.addEventListener('submit', (e) => this.handleSubmit(e));

        // Skills input enhancement
        this.initializeSkillsInput();

        // Phone number formatting
        this.initializePhoneFormatting();

        // Salary formatting
        this.initializeSalaryFormatting();
    }

    updatePreview() {
        const nameValue = document.getElementById('name')?.value || 'Candidate Name';
        const positionValue = document.getElementById('current_position')?.value || 'Position';
        const experienceValue = document.getElementById('experience_years')?.value || '0';
        const salaryValue = document.getElementById('expected_salary')?.value;

        // Update preview elements
        if (this.previewElements.initial) {
            this.previewElements.initial.textContent = nameValue.charAt(0).toUpperCase() || '?';
        }
        
        if (this.previewElements.name) {
            this.previewElements.name.textContent = nameValue;
        }
        
        if (this.previewElements.position) {
            this.previewElements.position.textContent = positionValue;
        }
        
        if (this.previewElements.experience) {
            this.previewElements.experience.textContent = `${experienceValue} years`;
        }
        
        if (this.previewElements.salary) {
            if (salaryValue) {
                this.previewElements.salary.textContent = `₹${parseInt(salaryValue).toLocaleString()}`;
            } else {
                this.previewElements.salary.textContent = 'Not specified';
            }
        }
    }

    initializeSkillsInput() {
        const skillsInput = document.getElementById('skills');
        if (!skillsInput) return;

        // Add skill suggestions
        const commonSkills = [
            'JavaScript', 'Python', 'Java', 'React', 'Angular', 'Vue.js', 'Node.js',
            'Django', 'Flask', 'Spring Boot', 'AWS', 'Azure', 'Docker', 'Kubernetes',
            'MongoDB', 'PostgreSQL', 'MySQL', 'Redis', 'Git', 'Jenkins', 'CI/CD',
            'Machine Learning', 'Data Science', 'DevOps', 'Agile', 'Scrum'
        ];

        // Create skills suggestion dropdown
        const suggestionContainer = document.createElement('div');
        suggestionContainer.className = 'skills-suggestions';
        suggestionContainer.style.cssText = `
            position: relative;
            margin-top: 5px;
        `;

        const suggestionList = document.createElement('div');
        suggestionList.className = 'suggestion-list';
        suggestionList.style.cssText = `
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        `;

        suggestionContainer.appendChild(suggestionList);
        skillsInput.parentNode.appendChild(suggestionContainer);

        // Show suggestions on focus
        skillsInput.addEventListener('focus', () => {
            this.showSkillSuggestions(commonSkills, suggestionList, skillsInput);
        });

        // Hide suggestions on blur (with delay for clicking)
        skillsInput.addEventListener('blur', () => {
            setTimeout(() => {
                suggestionList.style.display = 'none';
            }, 200);
        });
    }

    showSkillSuggestions(skills, container, input) {
        const currentSkills = input.value.toLowerCase().split(',').map(s => s.trim());
        const lastSkill = currentSkills[currentSkills.length - 1];
        
        const filteredSkills = skills.filter(skill => 
            skill.toLowerCase().includes(lastSkill) && 
            !currentSkills.includes(skill.toLowerCase())
        );

        container.innerHTML = '';
        
        if (filteredSkills.length > 0) {
            filteredSkills.forEach(skill => {
                const item = document.createElement('div');
                item.className = 'suggestion-item';
                item.textContent = skill;
                item.style.cssText = `
                    padding: 8px 12px;
                    cursor: pointer;
                    border-bottom: 1px solid #f0f0f0;
                `;
                
                item.addEventListener('mouseenter', () => {
                    item.style.backgroundColor = '#f8f9fa';
                });
                
                item.addEventListener('mouseleave', () => {
                    item.style.backgroundColor = 'white';
                });
                
                item.addEventListener('click', () => {
                    this.addSkillToInput(skill, input);
                    container.style.display = 'none';
                });
                
                container.appendChild(item);
            });
            
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }

    addSkillToInput(skill, input) {
        const currentSkills = input.value.split(',').map(s => s.trim()).filter(s => s);
        currentSkills[currentSkills.length - 1] = skill;
        input.value = currentSkills.join(', ') + ', ';
        input.focus();
    }

    initializePhoneFormatting() {
        const phoneInput = document.getElementById('phone');
        if (!phoneInput) return;

        phoneInput.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            // Format as +91-XXXXX-XXXXX
            if (value.length >= 10) {
                if (value.startsWith('91')) {
                    value = value.substring(2);
                }
                value = `+91-${value.substring(0, 5)}-${value.substring(5, 10)}`;
            } else if (value.length >= 5) {
                value = `+91-${value.substring(0, 5)}-${value.substring(5)}`;
            } else if (value.length > 0) {
                value = `+91-${value}`;
            }
            
            e.target.value = value;
        });
    }

    initializeSalaryFormatting() {
        const salaryInput = document.getElementById('expected_salary');
        if (!salaryInput) return;

        salaryInput.addEventListener('blur', (e) => {
            const value = parseInt(e.target.value);
            if (value) {
                // Format with commas
                e.target.value = value.toLocaleString();
            }
        });

        salaryInput.addEventListener('focus', (e) => {
            // Remove formatting for editing
            e.target.value = e.target.value.replace(/,/g, '');
        });
    }

    initializeValidation() {
        const emailInput = document.getElementById('email');
        const phoneInput = document.getElementById('phone');
        const linkedinInput = document.getElementById('linkedin_profile');

        // Email validation
        emailInput?.addEventListener('blur', (e) => {
            this.validateEmail(e.target);
        });

        // Phone validation
        phoneInput?.addEventListener('blur', (e) => {
            this.validatePhone(e.target);
        });

        // LinkedIn validation
        linkedinInput?.addEventListener('blur', (e) => {
            this.validateLinkedIn(e.target);
        });
    }

    validateEmail(input) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const isValid = !input.value || emailRegex.test(input.value);
        
        this.setFieldValidation(input, isValid, 'Please enter a valid email address');
    }

    validatePhone(input) {
        const phoneRegex = /^\+91-\d{5}-\d{5}$/;
        const isValid = !input.value || phoneRegex.test(input.value);
        
        this.setFieldValidation(input, isValid, 'Please enter a valid phone number (+91-XXXXX-XXXXX)');
    }

    validateLinkedIn(input) {
        const linkedinRegex = /^https:\/\/(www\.)?linkedin\.com\/in\/[a-zA-Z0-9-]+\/?$/;
        const isValid = !input.value || linkedinRegex.test(input.value);
        
        this.setFieldValidation(input, isValid, 'Please enter a valid LinkedIn profile URL');
    }

    setFieldValidation(input, isValid, errorMessage) {
        const existingError = input.parentNode.querySelector('.validation-error');
        
        if (existingError) {
            existingError.remove();
        }
        
        if (!isValid) {
            input.classList.add('is-invalid');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'validation-error';
            errorDiv.style.cssText = `
                color: #dc3545;
                font-size: 0.875rem;
                margin-top: 5px;
            `;
            errorDiv.textContent = errorMessage;
            
            input.parentNode.appendChild(errorDiv);
        } else {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        }
    }

    handleSubmit(event) {
        // Validate all fields before submission
        const emailInput = document.getElementById('email');
        const phoneInput = document.getElementById('phone');
        const linkedinInput = document.getElementById('linkedin_profile');

        let isValid = true;

        if (emailInput?.value) {
            this.validateEmail(emailInput);
            if (emailInput.classList.contains('is-invalid')) {
                isValid = false;
            }
        }

        if (phoneInput?.value) {
            this.validatePhone(phoneInput);
            if (phoneInput.classList.contains('is-invalid')) {
                isValid = false;
            }
        }

        if (linkedinInput?.value) {
            this.validateLinkedIn(linkedinInput);
            if (linkedinInput.classList.contains('is-invalid')) {
                isValid = false;
            }
        }

        if (!isValid) {
            event.preventDefault();
            this.showToast('Please fix the validation errors before submitting', 'error');
            return false;
        }

        // Show loading state
        const submitBtn = this.form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Saving...';
        }

        return true;
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#007bff'};
            color: white;
            border-radius: 4px;
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new CandidateFormManager();
});

// Add CSS for validation states
const style = document.createElement('style');
style.textContent = `
    .is-invalid {
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
    }
    
    .is-valid {
        border-color: #28a745 !important;
        box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25) !important;
    }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
