public class Calculator
{
    public int compute(int n)
    {
        utils helper = null;
        int sum = helper.sumToN(n);
        int avg = helper.average(sum, n);
        return avg;
    }
}