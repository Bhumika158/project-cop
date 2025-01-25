import React, { useState } from 'react';
import './style.css';

const App = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    projectName: '',
    description: '',
    benefits: '',
    requestorName: '',
    requestorEmail: '',
    sitTimeline: '',
    uatTimeline: '',
    prodTimeline: '',
    volumeDay: '',
    payloadSize: '',
    peakTPS: '',
    volumeCategory: 'RealTime',
    sourceApp: '',
    vendorAuthMechanism: 'mTLS+OAuth',
    authJustification: '',
    sourceCNNonProd: '',
    sourceCNProd: '',
    pciData: 'No',
    dataClassification: 'Public',
    streamingNeeded: 'No',
    contentType: '',
    attachmentDocument: 'No',
    backendApp: '',
    devHost: '',
    devPort: '',
    sitHost: '',
    sitPort: '',
    uatHost: '',
    uatPort: '',
    prodHost: '',
    prodPort: '',
    backendAuth: 'mTLS',
    apiDisplayName: '',
    basePath: '',
    numApiPaths: '1',
    customApiCount: '',
    apiPaths: []
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleNextStep = () => setStep((prevStep) => prevStep + 1);
  const handlePreviousStep = () => setStep((prevStep) => prevStep - 1);

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Form submitted', formData);
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Project Intake Form</h1>
      </header>
      <main className="form-container">
        {step === 1 && (
          <div className="form-step">
            <h2>Step 1: Project Information</h2>
            <label>
              Project Name: <span className="required">*</span>
              <input
                type="text"
                name="projectName"
                value={formData.projectName}
                onChange={handleInputChange}
                required
              />
            </label>
            <label>
              Description: <span className="required">*</span>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                required
              ></textarea>
            </label>
            <label>
              Benefits: <span className="required">*</span>
              <textarea
                name="benefits"
                value={formData.benefits}
                onChange={handleInputChange}
                required
              ></textarea>
            </label>
            <label>
              Requestor Name: <span className="required">*</span>
              <input
                type="text"
                name="requestorName"
                value={formData.requestorName}
                onChange={handleInputChange}
                required
              />
            </label>
            <label>
              Requestor Email: <span className="required">*</span>
              <input
                type="email"
                name="requestorEmail"
                value={formData.requestorEmail}
                onChange={handleInputChange}
                required
              />
            </label>
            <button type="button" onClick={handleNextStep}>
              Next
            </button>
          </div>
        )}
        {step === 2 && (
          <div className="form-step">
            <h2>Step 2: Timeline Information</h2>
            <label>
              SIT Release Date:
              <input
                type="date"
                name="sitTimeline"
                value={formData.sitTimeline}
                onChange={handleInputChange}
              />
            </label>
            <label>
              UAT Release Date:
              <input
                type="date"
                name="uatTimeline"
                value={formData.uatTimeline}
                onChange={handleInputChange}
              />
            </label>
            <label>
              PROD Release Date:
              <input
                type="date"
                name="prodTimeline"
                value={formData.prodTimeline}
                onChange={handleInputChange}
              />
            </label>
            <button type="button" onClick={handlePreviousStep}>
              Back
            </button>
            <button type="button" onClick={handleNextStep}>
              Next
            </button>
          </div>
        )}
        {step === 3 && (
          <div className="form-step">
            <h2>Step 3: Review & Submit</h2>
            <button type="button" onClick={handlePreviousStep}>
              Back
            </button>
            <button type="submit" onClick={handleSubmit}>
              Submit
            </button>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
