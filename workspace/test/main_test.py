from main import main

def test_main():
    """
    Unit test for the main function.
    
    This function checks if the main function prints 'hello' to the console.
    """
    captured_output = io.StringIO()
    sys.stdout = captured_output
    main()
    sys.stdout = sys.__stdout__
    assert captured_output.getvalue() == "hello\n"