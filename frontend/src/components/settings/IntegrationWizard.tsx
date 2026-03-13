import { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Alert,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
} from '@mui/material'
import { Check as CheckIcon } from '@mui/icons-material'

export interface IntegrationField {
  name: string
  label: string
  type: 'text' | 'password' | 'url' | 'number' | 'boolean' | 'select'
  required?: boolean
  default?: any
  placeholder?: string
  helpText?: string
  options?: Array<{ value: string; label: string }>
}

export interface IntegrationMetadata {
  id: string
  name: string
  category: string
  description: string
  functionality_type?: string
  has_ui?: boolean
  icon?: string
  fields: IntegrationField[]
  docs_url?: string
}

interface IntegrationWizardProps {
  open: boolean
  onClose: () => void
  integration: IntegrationMetadata
  onSave: (integrationId: string, config: Record<string, any>) => Promise<void>
  existingConfig?: Record<string, any>
}

export default function IntegrationWizard({
  open,
  onClose,
  integration,
  onSave,
  existingConfig = {},
}: IntegrationWizardProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [config, setConfig] = useState<Record<string, any>>(existingConfig)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const steps = ['Configuration', 'Review']

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1)
  }

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1)
  }

  const handleFieldChange = (fieldName: string, value: any) => {
    setConfig({ ...config, [fieldName]: value })
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await onSave(integration.id, config)
      onClose()
      // Reset state
      setActiveStep(0)
      setConfig({})
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    setActiveStep(0)
    setConfig(existingConfig)
    setError(null)
    onClose()
  }

  const isStepComplete = (step: number) => {
    if (step === 0) {
      // Check if all required fields are filled
      return integration.fields
        .filter((f) => f.required)
        .every((f) => config[f.name] && config[f.name] !== '')
    }
    return true
  }

  const renderField = (field: IntegrationField) => {
    const value = config[field.name] ?? field.default ?? ''

    switch (field.type) {
      case 'boolean':
        return (
          <FormControlLabel
            key={field.name}
            control={
              <Switch
                checked={Boolean(value)}
                onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              />
            }
            label={field.label}
          />
        )

      case 'select':
        return (
          <FormControl key={field.name} fullWidth margin="normal">
            <InputLabel>{field.label}</InputLabel>
            <Select
              value={value}
              label={field.label}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
            >
              {field.options?.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
            {field.helpText && (
              <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5 }}>
                {field.helpText}
              </Typography>
            )}
          </FormControl>
        )

      case 'number':
        return (
          <TextField
            key={field.name}
            fullWidth
            type="number"
            label={field.label}
            value={value}
            onChange={(e) => handleFieldChange(field.name, parseInt(e.target.value))}
            margin="normal"
            required={field.required}
            placeholder={field.placeholder}
            helperText={field.helpText}
          />
        )

      default:
        return (
          <TextField
            key={field.name}
            fullWidth
            type={field.type === 'password' ? 'password' : 'text'}
            label={field.label}
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            margin="normal"
            required={field.required}
            placeholder={field.placeholder}
            helperText={field.helpText}
          />
        )
    }
  }

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="body2" color="textSecondary" paragraph>
              {integration.description}
            </Typography>
            {integration.docs_url && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Documentation:{' '}
                <a href={integration.docs_url} target="_blank" rel="noopener noreferrer">
                  {integration.docs_url}
                </a>
              </Alert>
            )}
            {integration.fields.map((field) => renderField(field))}
          </Box>
        )

      case 1:
        return (
          <Box>
            <Typography variant="body2" color="textSecondary" paragraph>
              Review your configuration before saving:
            </Typography>
            <Box sx={{ mt: 2 }}>
              {integration.fields.map((field) => {
                const value = config[field.name]
                const displayValue =
                  field.type === 'password' ? '••••••••' : value?.toString() || '(not set)'
                
                return (
                  <Box key={field.name} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2">{field.label}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {displayValue}
                    </Typography>
                  </Box>
                )
              })}
            </Box>
          </Box>
        )

      default:
        return null
    }
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Configure {integration.name}
        <Chip
          label={integration.category}
          size="small"
          color="error"
          sx={{ ml: 2 }}
        />
      </DialogTitle>

      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {renderStepContent(activeStep)}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={saving}>
          Cancel
        </Button>
        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={saving}>
            Back
          </Button>
        )}
        {activeStep < steps.length - 1 ? (
          <Button
            variant="contained"
            color="error"
            onClick={handleNext}
            disabled={!isStepComplete(activeStep)}
          >
            Next
          </Button>
        ) : (
          <Button
            variant="contained"
            color="error"
            onClick={handleSave}
            disabled={saving}
            startIcon={<CheckIcon />}
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  )
}

